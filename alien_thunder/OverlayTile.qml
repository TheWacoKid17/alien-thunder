import QtQuick
import QtQuick.Window
import org.kde.layershell as LayerShell

Window {
    id: tile

    required property string item
    required property var backend

    readonly property var cfg: backend.config.items[item]
    readonly property bool locked: backend.config.locked
    readonly property var value: backend.values[item]
    readonly property bool isTemp: item.endsWith("_temp")
    readonly property bool isFan: item.endsWith("_fan")
    property int mx: 0
    property int my: 0
    property string placedAs: ""

    width: 168
    height: 56
    color: "transparent"
    visible: false
    flags: Qt.FramelessWindowHint | (locked ? Qt.WindowTransparentForInput : 0)

    LayerShell.Window.scope: "alien-thunder-" + item
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorLeft
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone
    LayerShell.Window.exclusionZone: -1

    function screenNamed(name) {
        for (const s of Qt.application.screens)
            if (s.name === name) return s
        return Qt.application.screens[0]
    }

    function clampTo(s) {
        mx = Math.max(0, Math.min(mx, s.width - width))
        my = Math.max(0, Math.min(my, s.height - height))
    }

    // A layer surface takes its screen and margins when it's created, so moving it to
    // another screen, or turning click-through on and off, means creating it again.
    function place() {
        const key = JSON.stringify([cfg, locked])
        if (key === placedAs) return
        placedAs = key
        visible = false
        if (!cfg.shown) return
        const s = screenNamed(cfg.screen)
        backend.putOnScreen(tile, s.name)
        mx = cfg.x
        my = cfg.y
        clampTo(s)
        LayerShell.Window.margins.left = mx
        LayerShell.Window.margins.top = my
        visible = true
    }

    // Margins set on a live surface only reach the compositor with the next frame,
    // so every move also changes something on screen.
    property int frame: 0
    function moveBy(dx, dy) {
        mx += dx
        my += dy
        LayerShell.Window.margins.left = mx
        LayerShell.Window.margins.top = my
        frame++
    }

    function drop() {
        const s = screen
        const cx = s.virtualX + mx + width / 2
        const cy = s.virtualY + my + height / 2
        let target = s
        for (const o of Qt.application.screens)
            if (cx >= o.virtualX && cx < o.virtualX + o.width && cy >= o.virtualY && cy < o.virtualY + o.height)
                target = o
        mx = Math.round(mx + s.virtualX - target.virtualX)
        my = Math.round(my + s.virtualY - target.virtualY)
        clampTo(target)
        backend.place(item, target.name, mx, my)
        if (target !== s) {
            placedAs = ""
            place()
        } else {
            moveBy(0, 0)
        }
    }

    function severity() {
        if (value === undefined || value === null) return 0
        if (isTemp) return value >= 90 ? 2 : value >= 75 ? 1 : 0
        if (item === "ram") return value >= 95 ? 2 : value >= 85 ? 1 : 0
        return 0
    }

    Connections {
        target: tile.backend
        function onConfigChanged() { tile.place() }
    }

    Component.onCompleted: place()

    Rectangle {
        anchors.fill: parent
        radius: 10
        color: "#d90b0d10"
        border.width: 1
        border.color: drag.pressed ? "#00e5ff" : tile.severity() === 2 ? "#ff3b30" : "#3300e5ff"

        Column {
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 1
            Text {
                text: tile.backend.labels[tile.item].toUpperCase()
                color: "#8a9ba8"
                font.pixelSize: 11
                font.bold: true
                font.letterSpacing: 1
            }
            Text {
                text: tile.isTemp ? "°C" : tile.isFan ? "rpm" : "%"
                color: "#5c6b77"
                font.pixelSize: 10
            }
        }

        Text {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            text: tile.value === undefined || tile.value === null ? "--" : tile.value
            color: ["#e8f7ff", "#ffb020", "#ff3b30"][tile.severity()]
            font.family: "monospace"
            font.pixelSize: 28
            font.bold: true
        }

        // Changes with every move so the new margins go out with a fresh frame.
        Rectangle {
            width: 1
            height: 1
            color: tile.frame % 2 ? "#01000000" : "#02000000"
        }
    }

    MouseArea {
        id: drag
        anchors.fill: parent
        enabled: !tile.locked
        cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        property point start
        onPressed: (m) => start = Qt.point(m.x, m.y)
        onPositionChanged: (m) => tile.moveBy(m.x - start.x, m.y - start.y)
        onReleased: tile.drop()
    }
}
