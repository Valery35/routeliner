"""Заглушка qgis для чтения описаний инструментов без QGIS.

Каждое имя из qgis.core и qgis.PyQt становится символом, который помнит
свой путь (Qgis.ProcessingSourceType.VectorLine) и вызов с аргументами.
Базовые классы Processing - настоящие классы, у которых addParameter
и addOutput только записывают параметр. Этого хватает, чтобы вызвать
initAlgorithm каждого инструмента и прочитать его параметры как есть.

Заглушка ставится на время и снимается вместе со всеми модулями
routeliner, которые успели её увидеть, чтобы не мешать другим тестам.
"""
from __future__ import annotations

import contextlib
import sys
import types


class Sym:
    """Имя из qgis: путь, обращение к атрибуту, вызов, объединение флагов."""

    def __init__(self, path):
        self._path = path

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Sym(f"{self._path}.{name}")

    def __call__(self, *args, **kwargs):
        return Call(self._path, args, kwargs)

    def __or__(self, other):
        return Sym(f"{self._path}|{getattr(other, '_path', other)}")

    __ror__ = __or__

    def __repr__(self):
        return self._path

    def __hash__(self):
        return hash(self._path)

    def __eq__(self, other):
        return isinstance(other, Sym) and other._path == self._path

    @property
    def leaf(self):
        return self._path.rsplit(".", 1)[-1]


class Call(Sym):
    """Вызов конструктора qgis: имя класса и аргументы."""

    def __init__(self, path, args, kwargs):
        super().__init__(path)
        self.args, self.kwargs = args, kwargs
        self.flag_text = ""

    def flags(self):
        return Sym("flags")

    def setFlags(self, value):
        self.flag_text = repr(value)


class QgsProcessingAlgorithm:
    def __init__(self):
        self._params, self._outputs = [], []

    def addParameter(self, p):
        self._params.append(p)
        return True

    def addOutput(self, o):
        self._outputs.append(o)
        return True

    def parameterDefinition(self, name):
        return next((p for p in self._params if p.args and p.args[0] == name), None)

    def parameterDefinitions(self):
        return list(self._params)

    def flags(self):
        return Sym("Qgis.ProcessingAlgorithmFlag.Default")


class QgsProcessingProvider:
    def __init__(self):
        self.algs = []

    def addAlgorithm(self, alg):
        self.algs.append(alg)


class QgsProcessingLayerPostProcessorInterface:
    def __init__(self, *a, **k):
        pass


_CLASSES = {c.__name__: c for c in (QgsProcessingAlgorithm, QgsProcessingProvider,
                                    QgsProcessingLayerPostProcessorInterface)}


def _module(name):
    m = types.ModuleType(name)
    m.__path__ = []

    def getattr_(attr):
        if attr.startswith("__"):
            raise AttributeError(attr)
        return _CLASSES.get(attr) or Sym(attr)
    m.__getattr__ = getattr_
    return m


STUB_NAMES = ("qgis", "qgis.core", "qgis.gui", "qgis.PyQt", "qgis.PyQt.QtCore",
              "qgis.PyQt.QtGui", "qgis.PyQt.QtWidgets", "processing")


_STUBBED_PREFIX = ("qgis.", "routeliner.processing", "routeliner.layers", "routeliner.about",
                   "routeliner.resources")


@contextlib.contextmanager
def stubbed_qgis():
    """Ставит заглушку и по выходе возвращает sys.modules как было."""
    saved = dict(sys.modules)
    for n in STUB_NAMES:
        sys.modules[n] = _module(n)
    for n in [n for n in sys.modules if n == "routeliner" or n.startswith("routeliner.")]:
        if n.startswith(("routeliner.processing", "routeliner.layers", "routeliner.about",
                          "routeliner.resources")):
            del sys.modules[n]
    try:
        yield
    finally:
        # убираются только заглушки и модули routeliner, которые их видели.
        # Прочие модули (numpy) остаются: второй раз numpy не грузится.
        for n in list(sys.modules):
            if n in STUB_NAMES or n.startswith(_STUBBED_PREFIX):
                del sys.modules[n]
        for n in STUB_NAMES + tuple(k for k in saved if k.startswith(_STUBBED_PREFIX)):
            if n in saved:
                sys.modules[n] = saved[n]
        pkg = sys.modules.get("routeliner")
        for sub in ("processing", "layers", "about", "resources"):
            if pkg is not None and f"routeliner.{sub}" not in saved and hasattr(pkg, sub):
                delattr(pkg, sub)
