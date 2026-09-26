import QtQuick
import QtQuick.Window
import org.kde.layershell as LayerShell

Window {
    id: bar

    required property var overlay
    required property var backend

    property int mx: 0
    property int my: 0
    property int ox: 0  // the top-left corner of the screen the bar is on
    property int oy: 0
    property int frame: 0

    width: content.implicitWidth
    height: content.implicitHeight
    color: "transparent"
    visible: false

    LayerShell.Window.scope: "alien-thunder-overlay"
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorLeft
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone
    LayerShell.Window.exclusionZone: -1

    function setMargins() {
        LayerShell.Window.margins.left = mx
        LayerShell.Window.margins.top = my
        // New margins only reach the compositor with the next frame, so something on
        // screen has to change with them.
        frame++
    }

    // Never hidden and shown again to move: hiding destroys the surface, and Qt can still
    // deliver a pending repaint to it afterwards, which crashed the overlay. The screen is
    // set once, before the surface exists; moving to another screen restarts the overlay.
    function place(pos, first) {
        ox = pos.ox
        oy = pos.oy
        mx = pos.x
        my = pos.y
        if (first)
            LayerShell.Window.screen = backend.screenObject(pos.screen)
        setMargins()
    }

    Component.onCompleted: {
        place(backend.restore(bar), true)
        visible = true
    }
    onWidthChanged: if (visible) place(backend.restore(bar), false)

    BarContent {
        id: content
        anchors.fill: parent
        backend: bar.backend
        opacity: bar.overlay.dragging ? 0.55 : 1.0
        onCloseClicked: bar.backend.close()
    }

    // While dragging, a bright frame says "let go anywhere".
    Rectangle {
        anchors.fill: parent
        radius: 10
        color: "transparent"
        border.width: 2
        border.color: "#00e5ff"
        visible: bar.overlay.dragging
    }

    // Changes with every move so the new margins go out with a fresh frame.
    Rectangle {
        width: 1
        height: 1
        color: bar.frame % 2 ? "#01000000" : "#02000000"
    }

    MouseArea {
        id: drag
        anchors.fill: parent
        anchors.rightMargin: 30  // the ✕ has its own mouse area
        cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        property point start

        // The bar doesn't move while the button is down, so these coordinates stay
        // true for the whole drag.
        onPressed: (m) => start = Qt.point(m.x, m.y)
        onPositionChanged: (m) => {
            const dx = m.x - start.x
            const dy = m.y - start.y
            if (!bar.overlay.dragging && Math.abs(dx) + Math.abs(dy) < 4)
                return
            bar.overlay.dropX = bar.ox + bar.mx + dx
            bar.overlay.dropY = bar.oy + bar.my + dy
            bar.overlay.dragging = true
        }
        onReleased: {
            if (!bar.overlay.dragging)
                return
            const r = bar.backend.drop(bar, Math.round(bar.overlay.dropX), Math.round(bar.overlay.dropY))
            if (r.moved) {
                bar.backend.relaunch()
                return
            }
            bar.overlay.dragging = false
            bar.place(r, false)
        }
    }
}
