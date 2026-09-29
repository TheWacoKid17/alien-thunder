import QtQuick

// What the bar shows: the readings side by side, and the ✕ when showClose is set.
Item {
    id: content

    required property var backend
    property bool showClose: true
    signal closeClicked()

    implicitWidth: row.implicitWidth
    implicitHeight: 56

    function unit(key) {
        if (key.endsWith("_temp")) return "°C"
        if (key.endsWith("_fan")) return "rpm"
        if (key === "ram_gb") return "GB / " + (backend.values.ram_total_gb || "?")
        return "%"
    }

    function severity(key) {
        const v = backend.values[key]
        if (v === undefined || v === null) return 0
        if (key.endsWith("_temp")) return v >= 90 ? 2 : v >= 75 ? 1 : 0
        if (key === "ram" || key === "gpu_mem") return v >= 95 ? 2 : v >= 85 ? 1 : 0
        return 0
    }

    Rectangle {
        anchors.fill: parent
        radius: 10
        color: "#e00b0d10"
        border.width: 1
        border.color: "#3300e5ff"
    }

    Row {
        id: row
        height: parent.height
        leftPadding: 6
        rightPadding: content.showClose ? 4 : 12

        Text {
            anchors.verticalCenter: parent.verticalCenter
            width: 14
            text: "⋮"
            font.pixelSize: 22
            horizontalAlignment: Text.AlignHCenter
            color: "#5c6b77"
        }

        Repeater {
            model: content.backend.items.filter(k => content.backend.config.items[k])
            delegate: Row {
                required property string modelData
                required property int index
                height: row.height

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
                                text: content.backend.labels[modelData].toUpperCase()
                                color: "#8a9ba8"
                                font.pixelSize: 11
                                font.bold: true
                                font.letterSpacing: 1
                            }
                            Text {
                                text: content.unit(modelData)
                                color: "#5c6b77"
                                font.pixelSize: 10
                            }
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            // Room for the widest reading, so a new digit never resizes the
                            // window: resizing a layer surface crashed Qt (no screen for a moment).
                            width: widest.advanceWidth
                            horizontalAlignment: Text.AlignRight
                            TextMetrics {
                                id: widest
                                font.family: "monospace"
                                font.pixelSize: 28
                                font.bold: true
                                text: modelData.endsWith("_fan") ? "8888" : modelData === "ram_gb" ? "88.8" : "888"
                            }
                            text: {
                                const v = content.backend.values[modelData]
                                return v === undefined || v === null ? "--" : v
                            }
                            color: ["#e8f7ff", "#ffb020", "#ff3b30"][content.severity(modelData)]
                            font.family: "monospace"
                            font.pixelSize: 28
                            font.bold: true
                        }
                    }
                }
            }
        }

        Item {
            visible: content.showClose
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
                onClicked: content.closeClicked()
            }
        }
    }
}
