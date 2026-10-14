"""Prueba en Play (04/10), con L_FactoryDemo abierto en el editor: musica y sonidos se silencian por separado.

M (AFactoryDemoHUD::ToggleMusic) silencia solo la musica, N (ToggleSounds) solo los demas sonidos, y el boton del panel
de informacion (ToggleMute) todo junto o todo de vuelta. Comprueba tambien que la musica (S_MusicaFabrica) es de
SC_Musica y los sonidos de SC_Sonidos (apply_sonidos.py). No guarda nada. Informe: Docs/sonidos_play.json.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

docs = Path(unreal.Paths.project_dir()).resolve() / "Docs"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
report = {"passed": False, "checks": {}}
state = {"phase": "start", "t": time.monotonic(), "start": time.monotonic()}


def check(name, ok, **values):
    report["checks"][name] = dict(passed=bool(ok), **values)


def finish():
    report["passed"] = bool(report["checks"]) and all(c["passed"] for c in report["checks"].values()) and "error" not in report
    (docs / "sonidos_play.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    unreal.unregister_slate_post_tick_callback(state["handle"])
    if unreal.EditorLevelLibrary.get_pie_worlds(False):
        levels.editor_request_end_play()


def tick(delta):
    try:
        if time.monotonic() - state["start"] > 60:
            raise RuntimeError("La prueba tardo demasiado")
        if state["phase"] == "start":
            levels.editor_request_begin_play()
            state.update(phase="spawn", t=time.monotonic())
        elif state["phase"] == "spawn" and time.monotonic() - state["t"] > 4:
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            pc = unreal.GameplayStatics.get_player_controller(worlds[0], 0) if worlds else None
            hud = pc.get_hud() if pc else None
            if hud is None:
                return
            music = unreal.load_asset("/Game/FactoryCtyco/Audio/S_MusicaFabrica")
            check("musica_es_sc_musica", music.get_editor_property("sound_class_object").get_name() == "SC_Musica")
            hud.toggle_music()
            check("m_silencia_solo_musica", hud.is_music_muted() and not hud.is_sounds_muted())
            hud.toggle_music()
            hud.toggle_sounds()
            check("n_silencia_solo_sonidos", hud.is_sounds_muted() and not hud.is_music_muted())
            hud.toggle_sounds()
            hud.toggle_mute()
            all_off = hud.is_music_muted() and hud.is_sounds_muted()
            hud.toggle_mute()
            check("panel_silencia_todo_y_vuelve", all_off and not hud.is_music_muted() and not hud.is_sounds_muted())
            finish()
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error("[SONIDOS_PLAY] " + report["error"])
        finish()


state["handle"] = unreal.register_slate_post_tick_callback(tick)
