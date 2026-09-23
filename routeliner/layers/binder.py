"""Динамические слои событий.

Привязка (Binding) хранит параметры алгоритма постановки событий, в которых
слои заданы идентификаторами слоёв проекта. Она слушает слой маршрутов,
таблицу событий и ведомость (правки, сохранение, перезагрузку, изменение
файла CSV/Excel на диске), после паузы пересчитывает события тем же
алгоритмом Processing, что и обычный запуск, и перезаполняет два слоя
в памяти: события и ошибки.

Привязки записываются в проект; при открытии проекта слои в памяти
(QGIS сохраняет их пустыми) заполняются заново.
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

from qgis.core import (Qgis, QgsFeature, QgsMessageLog, QgsProcessingContext,
                       QgsProcessingFeedback, QgsProject, QgsProviderRegistry,
                       QgsVectorLayer)
from qgis.PyQt.QtCore import QFileSystemWatcher, QObject, QTimer

from ..i18n import tr

TAG = "Routeliner"
SCOPE = "routeliner"
KEY = "bindings"
DEBOUNCE_MS = 400
LAYER_KEYS = ("ROUTES", "EVENTS", "LEDGER")
_SIGNALS = ("dataChanged", "featureAdded", "featuresDeleted", "geometryChanged",
            "attributeValueChanged", "attributeAdded", "attributeDeleted",
            "afterCommitChanges", "afterRollBack", "committedFeaturesAdded",
            "committedFeaturesRemoved", "committedGeometriesChanges",
            "committedAttributeValuesChanges")

manager: Optional["BindingManager"] = None     # ставит модуль при загрузке


def log(msg: str, level=Qgis.MessageLevel.Info):
    QgsMessageLog.logMessage(msg, TAG, level)


def _file_of(layer: QgsVectorLayer) -> Optional[str]:
    """Путь к файлу источника для CSV/Excel/GPKG/SHP, иначе None."""
    try:
        parts = QgsProviderRegistry.instance().decodeUri(layer.providerType(), layer.source())
    except Exception:
        return None
    path = parts.get("path") or ""
    if path.startswith("file:"):
        from qgis.PyQt.QtCore import QUrl
        path = QUrl(path).toLocalFile()
    return path or None


class Binding(QObject):
    def __init__(self, mgr: "BindingManager", cfg: dict):
        super().__init__()
        self.mgr = mgr
        self.cfg = cfg
        self.project: QgsProject = mgr.project
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(DEBOUNCE_MS)
        self.timer.timeout.connect(self.recompute)
        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(self._file_changed)
        self._conns: list = []
        self.sources: dict = {}
        self.last = ""

    # ------------------------------------------------------------ слои
    @property
    def out_layer(self) -> Optional[QgsVectorLayer]:
        return self.project.mapLayer(self.cfg.get("out_id") or "")

    @property
    def err_layer(self) -> Optional[QgsVectorLayer]:
        return self.project.mapLayer(self.cfg.get("err_id") or "")

    def connect_sources(self):
        self.disconnect_sources()
        for key in LAYER_KEYS:
            lid = self.cfg["params"].get(key)
            lyr = self.project.mapLayer(lid) if lid else None
            if lyr is None:
                continue
            self.sources[key] = lyr
            for name in _SIGNALS:
                sig = getattr(lyr, name, None)
                if sig is None:
                    continue

                def slot(*_args):
                    self.schedule()
                sig.connect(slot)
                self._conns.append((sig, slot))
            path = _file_of(lyr)
            if path and lyr.providerType() in ("delimitedtext", "ogr"):
                self.watcher.addPath(path)

    def disconnect_sources(self):
        for sig, slot in self._conns:
            try:
                sig.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        self._conns = []
        files = self.watcher.files()
        if files:
            self.watcher.removePaths(files)
        self.sources = {}

    def _file_changed(self, path):
        # редакторы часто заменяют файл целиком — путь нужно добавить снова
        QTimer.singleShot(200, lambda: self.watcher.addPath(path))
        for lyr in self.sources.values():
            if _file_of(lyr) == path and not lyr.isEditable():
                lyr.dataProvider().reloadData()
                lyr.reload()
        self.schedule()

    def schedule(self):
        self.timer.start()

    # ------------------------------------------------------------ пересчёт
    def recompute(self) -> dict:
        import processing
        missing = [k for k in ("ROUTES", "EVENTS") if self.project.mapLayer(self.cfg["params"].get(k) or "") is None]
        if missing:
            self.last = tr("нет слоя: {names}").format(names=", ".join(missing))
            log(f"{self.cfg['name']}: {self.last}", Qgis.MessageLevel.Warning)
            return {}
        ctx = QgsProcessingContext()
        ctx.setProject(self.project)
        fb = QgsProcessingFeedback()
        params = dict(self.cfg["params"], OUTPUT="memory:", ERRORS="memory:")
        try:
            res = processing.run(f"routeliner:{self.cfg['alg']}", params, context=ctx, feedback=fb)
        except Exception as e:  # ошибка параметров — в журнал, слой не трогаем
            self.last = tr("ошибка: {e}").format(e=e)
            log(f"{self.cfg['name']}: {self.last}", Qgis.MessageLevel.Critical)
            return {}
        out, err = res["OUTPUT"], res.get("ERRORS")
        if isinstance(out, str):
            out = ctx.getMapLayer(out)
        if isinstance(err, str):
            err = ctx.getMapLayer(err)
        n_ok = self._fill(self.out_layer, out)
        n_err = self._fill(self.err_layer, err) if err is not None else 0
        self.last = tr("поставлено {a}, ошибок {b}").format(a=n_ok, b=n_err)
        log(f"{self.cfg['name']}: {self.last}")
        return {"placed": n_ok, "errors": n_err}

    @staticmethod
    def _fill(target: Optional[QgsVectorLayer], src: QgsVectorLayer) -> int:
        if target is None or src is None:
            return 0
        pr = target.dataProvider()
        if [f.name() for f in target.fields()] != [f.name() for f in src.fields()]:
            pr.deleteAttributes(list(range(target.fields().count())))
            target.updateFields()
            pr.addAttributes(list(src.fields()))
            target.updateFields()
        pr.truncate()
        feats = []
        for f in src.getFeatures():
            g = QgsFeature(target.fields())
            g.setAttributes(f.attributes())
            if f.hasGeometry():
                g.setGeometry(f.geometry())
            feats.append(g)
        pr.addFeatures(feats)
        target.updateExtents()
        target.triggerRepaint()
        return len(feats)


class BindingManager(QObject):
    def __init__(self, project: Optional[QgsProject] = None, iface=None):
        super().__init__()
        self.project = project or QgsProject.instance()
        self.iface = iface
        self.bindings: dict = {}      # out_id -> Binding
        self._restoring = False
        p = self.project
        p.readProject.connect(self._on_read)
        p.cleared.connect(self.clear)
        p.layersWillBeRemoved.connect(self._on_remove)
        p.writeProject.connect(lambda *_: self.save())

    def unload(self):
        p = self.project
        for sig, slot in ((p.readProject, self._on_read), (p.cleared, self.clear),
                          (p.layersWillBeRemoved, self._on_remove)):
            try:
                sig.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        self.clear()

    # ------------------------------------------------------------ создание
    def add(self, alg: str, params: dict, name: str, crs, geometry: str) -> Binding:
        """params — параметры алгоритма (слои — идентификаторами слоёв проекта)."""
        out = QgsVectorLayer(f"{geometry}?crs={crs.authid() or crs.toWkt()}", name, "memory")
        err = QgsVectorLayer("None", tr("{name}, ошибки").format(name=name), "memory")
        for lyr in (out, err):
            lyr.setCustomProperty("routeliner/live", True)
        group = self._group()
        for lyr in (out, err):
            self.project.addMapLayer(lyr, False)
            group.addLayer(lyr)
        cfg = {"id": uuid.uuid4().hex, "alg": alg, "name": name, "params": params,
               "out_id": out.id(), "err_id": err.id()}
        b = self._start(cfg)
        self.save()
        return b

    def _group(self):
        root = self.project.layerTreeRoot()
        g = root.findGroup("Routeliner")
        return g or root.insertGroup(0, "Routeliner")

    def _start(self, cfg) -> Binding:
        b = Binding(self, cfg)
        self.bindings[cfg["out_id"]] = b
        b.connect_sources()
        b.recompute()
        return b

    # ------------------------------------------------------------ проект
    def save(self):
        if self._restoring:
            return
        data = json.dumps([b.cfg for b in self.bindings.values()], ensure_ascii=False)
        self.project.writeEntry(SCOPE, KEY, data)

    def _on_read(self, *_):
        self.restore()

    def restore(self):
        self.clear()
        raw, ok = self.project.readEntry(SCOPE, KEY, "")
        if not ok or not raw:
            return
        self._restoring = True
        try:
            for cfg in json.loads(raw):
                if self.project.mapLayer(cfg.get("out_id", "")) is None:
                    log(tr("{name}: слой событий удалён из проекта, привязка пропущена").format(
                        name=cfg.get("name")),
                        Qgis.MessageLevel.Warning)
                    continue
                self._start(cfg)
        finally:
            self._restoring = False
        log(tr("восстановлено динамических слоёв: {n}").format(n=len(self.bindings)))

    def clear(self, *_):
        for b in self.bindings.values():
            b.timer.stop()
            b.disconnect_sources()
        self.bindings = {}

    def _on_remove(self, ids):
        ids = set(ids)
        changed = False
        for out_id in list(self.bindings):
            b = self.bindings[out_id]
            if out_id in ids:
                b.timer.stop()
                b.disconnect_sources()
                del self.bindings[out_id]
                changed = True
            elif any(lid in ids for lid in (b.cfg["params"].get(k) for k in LAYER_KEYS) if lid):
                log(tr("{name}: исходный слой удалён, пересчёт остановлен").format(name=b.cfg["name"]),
                    Qgis.MessageLevel.Warning)
                b.disconnect_sources()
        if changed:
            self.save()
