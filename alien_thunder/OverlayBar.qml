import QtQuick
import QtQuick.Window
import org.kde.layershell as LayerShell

Window {
    id: bar

    required property var backend

    readonly property var shown: backend.items.filter(k => backend.config.items[k])
    property int mx: 0
    property int my: 0
    property int frame: 0

    width: content.implicitWidth
    height: 56
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

    // A layer surface takes its screen when it's created, so a new screen means
    // hiding the bar and showing it again there.
    function place(pos) {
        visible = false
        mx = pos.x
        my = pos.y
        setMargins()
        visible = true
    }

    Component.onCompleted: place(backend.restore(bar))
    onWidthChanged: if (visible) place(backend.restore(bar))

    function severity(key) {
        const v = backend.values[key]
        if (v === undefined || v === null) return 0
        if (key.endsWith("_temp")) return v >= 90 ? 2 : v >= 75 ? 1 : 0
        if (key === "ram") return v >= 95 ? 2 : v >= 85 ? 1 : 0
        return 0
    }

    Rectangle {
        anchors.fill: parent
        radius: 10
        color: "#e00b0d10"
        border.width: 1
        border.color: drag.pressed ? "#00e5ff" : "#3300e5ff"
    }

    MouseArea {
        id: drag
        anchors.fill: parent
        cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        property point start
        onPressed: (m) => start = Qt.point(m.x, m.y)
        onPositionChanged: (m) => {
            bar.mx += m.x - start.x
            bar.my += m.y - start.y
            bar.setMargins()
        }
        onReleased: {
            const r = bar.backend.drop(bar, bar.mx, bar.my)
            if (r.moved) {
                bar.place(r)
            } else {
                bar.mx = r.x
                bar.my = r.y
                bar.setMargins()
            }
        }
    }

    Row {
        id: content
        height: parent.height
        leftPadding: 6
        rightPadding: 4

        // Grip; its shade flips with every move so the new position goes out with a frame.
        Text {
            anchors.verticalCenter: parent.verticalCenter
            width: 14
            text: "⋮"
            font.pixelSize: 22
            horizontalAlignment: Text.AlignHCenter
            color: bar.frame % 2 ? "#5c6b77" : "#5d6c78"
        }

        Repeater {
            model: bar.shown
            delegate: Row {
                required property string modelData
                required property int index
                height: content.height

                Rectangle {
                    visible: index > 0
                    width: 1
                    height: parent.height - 20
                    anchors.verticalCenter: parent.verticalCenter
                    color: "#2a3a44"
                }

                Item {
                    width: readout.implicitWidth + 24
                    height: parent.height

                    Row {
                        id: readout
                        anchors.centerIn: parent
                        spacing: 8

                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 1
                            Text {
                                text: bar.backend.labels[modelData].toUpperCase()
                                color: "#8a9ba8"
                                font.pixelSize: 11
                                font.bold: true
                                font.letterSpacing: 1
                            }
                            Text {
                                text: modelData.endsWith("_temp") ? "°C" : modelData.endsWith("_fan") ? "rpm" : "%"
                                color: "#5c6b77"
                                font.pixelSize: 10
                            }
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: {
                                const v = bar.backend.values[modelData]
                                return v === undefined || v === null ? "--" : v
                            }
                            color: ["#e8f7ff", "#ffb020", "#ff3b30"][bar.severity(modelData)]
                            font.family: "monospace"
                            font.pixelSize: 28
                            font.bold: true
                        }
                    }
                }
            }
        }

        // Turns the overlay off; the panel widget turns it back on.
        Item {
            width: 30
            height: parent.height

            Rectangle {
                anchors.centerIn: parent
                width: 22
                height: 22
                radius: 11
                color: closeArea.containsMouse ? "#ff3b30" : "transparent"
            }
            Text {
                anchors.centerIn: parent
                text: "✕"
                font.pixelSize: 13
                color: closeArea.containsMouse ? "white" : "#8a9ba8"
            }
            MouseArea {
                id: closeArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: bar.backend.close()
            }
        }
    }
}
