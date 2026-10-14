"""Se corre solo al abrir el editor (plugin Python de Unreal, Content/Python/init_unreal.py).

(07/10) El techo de la fabrica no se ve mientras se edita, solo en Play: sus piezas estan en la capa "Techo Fabrica"
(Scripts/apply_techo_solo_play.py), pero Unreal no guarda si una capa esta oculta y al abrir el nivel volvia a verse.
Aca se oculta cada vez que se abre un mapa (y una vez al arrancar, cuando el nivel ya cargo). Las capas solo ocultan
en el editor: en Play el techo esta. Para verlo mientras se edita: Window -> Layers, el ojo de "Techo Fabrica".
"""
import unreal

HIDDEN_LAYERS = ("Techo Fabrica",)


def hide_layers(*_):
    try:
        layers = unreal.get_editor_subsystem(unreal.LayersSubsystem)
        names = [str(n) for n in layers.add_all_layer_names_to()]
        hidden = [name for name in HIDDEN_LAYERS if name in names]
        for name in hidden:
            layers.set_layer_visibility(name, False)
        return bool(hidden)
    except Exception as error:
        unreal.log_warning(f"[init_unreal] no se pudo ocultar las capas: {error}")
        return True


def _on_map_opened(_filename, _as_template):
    hide_layers()


def _first_tick(_delta):
    # al arrancar el nivel todavia no cargo: se espera a que aparezcan sus capas (como mucho ~10 s de ticks)
    global _ticks
    _ticks += 1
    if hide_layers() or _ticks > 600:
        unreal.unregister_slate_post_tick_callback(_tick_handle)


_ticks = 0
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).on_map_opened.add_callable(_on_map_opened)
_tick_handle = unreal.register_slate_post_tick_callback(_first_tick)
