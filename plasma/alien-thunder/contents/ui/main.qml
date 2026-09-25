import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.extras as PlasmaExtras
import org.kde.plasma.plasma5support as P5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root

    // Written every two seconds by the alien-thunder service.
    property var sensors: ({})
    property var overlay: ({ running: false, locked: false, items: {} })
    property bool serviceDown: false

    readonly property url icon: Qt.resolvedUrl("../images/alien-thunder.png")
    readonly property var metrics: ["cpu_temp", "gpu_temp", "cpu_fan", "gpu_fan", "ram"]

    function label(key) {
        switch (key) {
        case "cpu_temp": return i18n("CPU")
        case "gpu_temp": return i18n("GPU")
        case "cpu_fan": return i18n("CPU fan")
        case "gpu_fan": return i18n("GPU fan")
        case "ram": return i18n("RAM")
        }
        return key
    }

    function unit(key) {
        if (key.endsWith("_temp")) return "°C"
        if (key.endsWith("_fan")) return i18nc("revolutions per minute", "rpm")
        return "%"
    }

    function value(key) {
        const v = sensors[key]
        return v === undefined || v === null ? "--" : String(v)
    }

    function color(key) {
        const v = sensors[key]
        if (v === undefined || v === null) return Kirigami.Theme.disabledTextColor
        if (key.endsWith("_temp")) {
            if (v >= 90) return Kirigami.Theme.negativeTextColor
            if (v >= 75) return Kirigami.Theme.neutralTextColor
        }
        if (key === "ram") {
            if (v >= 95) return Kirigami.Theme.negativeTextColor
            if (v >= 85) return Kirigami.Theme.neutralTextColor
        }
        return Kirigami.Theme.textColor
    }

    function shownOnPanel(key) {
        return Plasmoid.configuration["panel_" + key]
    }

    function quote(text) {
        return "'" + String(text).replace(/'/g, "'\\''") + "'"
    }

    // alien-thunder lives in ~/.local/bin, which plasmashell doesn't always have on PATH.
    component Shell: P5Support.DataSource {
        engine: "executable"
        function run(command) {
            connectSource("PATH=\"$HOME/.local/bin:$PATH\"; " + command)
        }
    }

    Shell {
        id: sensorSource
        onNewData: (source, data) => {
            disconnectSource(source)
            try {
                root.sensors = JSON.parse(data.stdout)
                root.serviceDown = false
            } catch (e) {
                root.serviceDown = true
            }
        }
    }

    Shell {
        id: overlaySource
        function refresh() { run("alien-thunder overlay status") }
        onNewData: (source, data) => {
            disconnectSource(source)
            try { root.overlay = JSON.parse(data.stdout) } catch (e) {}
        }
    }

    Shell {
        id: action
        // Every change is followed by a fresh read, so the switches show what really happened.
        onNewData: (source) => {
            disconnectSource(source)
            overlaySource.refresh()
            sensorSource.run("cat \"$XDG_RUNTIME_DIR/alien-thunder/sensors.json\"")
        }
    }

    Timer {
        interval: 2000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: sensorSource.run("cat \"$XDG_RUNTIME_DIR/alien-thunder/sensors.json\"")
    }

    onExpandedChanged: () => { if (root.expanded) overlaySource.refresh() }
    Component.onCompleted: overlaySource.refresh()

    Plasmoid.icon: icon
    toolTipMainText: "Alien Thunder"
    toolTipSubText: {
        if (serviceDown) return i18n("The alien-thunder service isn't running")
        const lines = metrics.map(k => label(k) + ": " + value(k) + " " + unit(k))
        lines.push(sensors.gmode ? i18n("G-Mode is on") : i18n("G-Mode is off"))
        return lines.join("\n")
    }

    compactRepresentation: MouseArea {
        id: compact
        hoverEnabled: true
        onClicked: root.expanded = !root.expanded

        Layout.minimumWidth: row.implicitWidth
        Layout.preferredWidth: row.implicitWidth

        RowLayout {
            id: row
            anchors.verticalCenter: parent.verticalCenter
            spacing: Kirigami.Units.smallSpacing * 2

            Item {
                Layout.preferredWidth: compact.height
                Layout.preferredHeight: compact.height

                Kirigami.Icon {
                    anchors.fill: parent
                    anchors.margins: 2
                    source: root.icon
                    active: compact.containsMouse
                }

                // G-Mode badge, white like the F1 key while it's on.
                Rectangle {
                    visible: !!root.sensors.gmode
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    width: Math.round(parent.height * 0.42)
                    height: width
                    radius: width / 2
                    color: "white"
                    border.color: "black"
                    PlasmaComponents3.Label {
                        anchors.centerIn: parent
                        text: "G"
                        color: "black"
                        font.bold: true
                        font.pixelSize: parent.height * 0.7
                    }
                }
            }

            Repeater {
                model: root.metrics.filter(k => root.shownOnPanel(k))
                delegate: ColumnLayout {
                    required property string modelData
                    spacing: -2
                    PlasmaComponents3.Label {
                        text: root.label(modelData).toUpperCase() + " " + root.unit(modelData)
                        font.pixelSize: Math.max(8, compact.height * 0.24)
                        opacity: 0.6
                        Layout.alignment: Qt.AlignHCenter
                    }
                    PlasmaComponents3.Label {
                        text: root.value(modelData)
                        color: root.color(modelData)
                        font.family: "monospace"
                        font.bold: true
                        font.pixelSize: Math.max(11, compact.height * 0.42)
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }
        }
    }

    fullRepresentation: PlasmaExtras.Representation {
        Layout.preferredWidth: Kirigami.Units.gridUnit * 22
        Layout.minimumWidth: Kirigami.Units.gridUnit * 18
        Layout.preferredHeight: content.implicitHeight + header.implicitHeight + Kirigami.Units.largeSpacing * 2
        collapseMarginsHint: true

        header: PlasmaExtras.PlasmoidHeading {
            RowLayout {
                anchors.fill: parent
                spacing: Kirigami.Units.largeSpacing
                Kirigami.Icon {
                    source: root.icon
                    Layout.preferredWidth: Kirigami.Units.iconSizes.medium
                    Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                }
                Kirigami.Heading {
                    text: "Alien Thunder"
                    level: 2
                    Layout.fillWidth: true
                }
                PlasmaComponents3.ToolButton {
                    icon.name: "preferences-desktop-color"
                    text: i18n("Lighting")
                    onClicked: {
                        action.run("setsid -f alien-thunder >/dev/null 2>&1")
                        root.expanded = false
                    }
                    PlasmaComponents3.ToolTip { text: i18n("Open the keyboard lighting editor") }
                }
            }
        }

        ColumnLayout {
            id: content
            anchors.fill: parent
            anchors.margins: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.largeSpacing

            PlasmaComponents3.Label {
                visible: root.serviceDown
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Kirigami.Theme.negativeTextColor
                text: i18n("No readings: the alien-thunder service isn't running. Start it with: systemctl --user start alien-thunder")
            }

            GridLayout {
                columns: 3
                Layout.fillWidth: true
                columnSpacing: Kirigami.Units.largeSpacing
                rowSpacing: Kirigami.Units.smallSpacing
                Repeater {
                    model: root.metrics
                    delegate: ColumnLayout {
                        required property string modelData
                        Layout.fillWidth: true
                        spacing: 0
                        PlasmaComponents3.Label {
                            text: root.label(modelData).toUpperCase() + " " + root.unit(modelData)
                            opacity: 0.6
                            font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                        }
                        PlasmaComponents3.Label {
                            text: root.value(modelData)
                            color: root.color(modelData)
                            font.family: "monospace"
                            font.bold: true
                            font.pixelSize: Kirigami.Units.gridUnit * 1.6
                        }
                    }
                }
            }

            Kirigami.Separator { Layout.fillWidth: true }

            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    PlasmaComponents3.Label { text: i18n("G-Mode"); font.bold: true }
                    PlasmaComponents3.Label {
                        text: i18n("Fans at full speed and the performance power profile. Same as Fn+F1.")
                        wrapMode: Text.Wrap
                        opacity: 0.7
                        font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                        Layout.fillWidth: true
                    }
                }
                PlasmaComponents3.Switch {
                    checked: !!root.sensors.gmode
                    onToggled: action.run("alien-thunder gmode " + (checked ? "on" : "off"))
                }
            }

            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    PlasmaComponents3.Label { text: i18n("Overlay"); font.bold: true }
                    PlasmaComponents3.Label {
                        text: i18n("Readouts that float above every window, games included. Drag them anywhere, on any screen.")
                        wrapMode: Text.Wrap
                        opacity: 0.7
                        font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                        Layout.fillWidth: true
                    }
                }
                PlasmaComponents3.Switch {
                    checked: !!root.overlay.running
                    onToggled: action.run("alien-thunder overlay " + (checked ? "on" : "off"))
                }
            }

            ColumnLayout {
                visible: !!root.overlay.running
                Layout.fillWidth: true
                Layout.leftMargin: Kirigami.Units.largeSpacing
                spacing: 0

                PlasmaComponents3.CheckBox {
                    text: i18n("Lock in place (clicks pass through)")
                    checked: !!root.overlay.locked
                    onToggled: action.run("alien-thunder overlay " + (checked ? "lock" : "unlock"))
                }
                Flow {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing
                    Repeater {
                        model: root.metrics
                        delegate: PlasmaComponents3.CheckBox {
                            required property string modelData
                            text: root.label(modelData)
                            checked: !!(root.overlay.items && root.overlay.items[modelData] && root.overlay.items[modelData].shown)
                            onToggled: action.run("alien-thunder overlay " + (checked ? "show " : "hide ") + modelData)
                        }
                    }
                }
            }
        }
    }
}
