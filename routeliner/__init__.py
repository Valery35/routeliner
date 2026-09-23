def classFactory(iface):
    from .plugin import RoutelinerPlugin
    return RoutelinerPlugin(iface)
