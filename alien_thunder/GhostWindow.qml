import QtQuick
import QtQuick.Window
import org.kde.layershell as LayerShell

// Covers one screen while the bar is being dragged, and lets every click through. Between
// drags it stays mapped at one pixel: hiding a window destroys its surface, and Qt can
// still deliver a pending repaint to it afterwards, which crashed the overlay.
Window {
    id: ghost

    required property var screenInfo
    required property var overlay
    required property var backend

    width: overlay.dragging ? screenInfo.width : 1
    height: overlay.dragging ? screenInfo.height : 1
    color: "transparent"
    flags: Qt.WindowTransparentForInput
    visible: true

    LayerShell.Window.scope: "alien-thunder-overlay-drag"
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorLeft
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone
    LayerShell.Window.exclusionZone: -1

    Component.onCompleted: LayerShell.Window.screen = backend.screenObject(screenInfo.name)

    BarContent {
        visible: ghost.overlay.dragging
        backend: ghost.backend
        showClose: false
        x: ghost.overlay.ghostX - ghost.screenInfo.x
        y: ghost.overlay.ghostY - ghost.screenInfo.y
        width: ghost.overlay.bar.width
        height: ghost.overlay.bar.height
    }
}
