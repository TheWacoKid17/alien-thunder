import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    id: page

    // The dialog hands every page every setting; this one only shows addresses.
    property bool cfg_panel_cpu_temp
    property bool cfg_panel_cpu_load
    property bool cfg_panel_gpu_temp
    property bool cfg_panel_gpu_mem
    property bool cfg_panel_cpu_fan
    property bool cfg_panel_gpu_fan
    property bool cfg_panel_ram
    property bool cfg_panel_ram_gb
    property bool cfg_overlay_cpu_temp
    property bool cfg_overlay_cpu_load
    property bool cfg_overlay_gpu_temp
    property bool cfg_overlay_gpu_mem
    property bool cfg_overlay_cpu_fan
    property bool cfg_overlay_gpu_fan
    property bool cfg_overlay_ram
    property bool cfg_overlay_ram_gb
    property bool cfg_panel_cpu_tempDefault
    property bool cfg_panel_cpu_loadDefault
    property bool cfg_panel_gpu_tempDefault
    property bool cfg_panel_gpu_memDefault
    property bool cfg_panel_cpu_fanDefault
    property bool cfg_panel_gpu_fanDefault
    property bool cfg_panel_ramDefault
    property bool cfg_panel_ram_gbDefault
    property bool cfg_overlay_cpu_tempDefault
    property bool cfg_overlay_cpu_loadDefault
    property bool cfg_overlay_gpu_tempDefault
    property bool cfg_overlay_gpu_memDefault
    property bool cfg_overlay_cpu_fanDefault
    property bool cfg_overlay_gpu_fanDefault
    property bool cfg_overlay_ramDefault
    property bool cfg_overlay_ram_gbDefault

    readonly property var wallets: [
        { name: "Bitcoin", address: "bc1q2nqp9d8lc0u6z7v9ag4u52sv9g9afepgyyrwu4", qr: "../images/donate-btc.png", networks: "" },
        // One address takes donations on every EVM network Vurto Swap supports.
        { name: i18n("EVM networks"), address: "0x930CD3e9de6F2dB03709667C9799d073b34FEaCc", qr: "../images/donate-evm.png",
          networks: "Ethereum · Optimism · BNB Chain · Gnosis · Polygon · Base · Arbitrum One · Avalanche · Unichain" },
    ]

    // QML has no clipboard API; a hidden text field can copy its own text.
    TextEdit {
        id: clipboard
        visible: false
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing * 2

        QQC2.Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: i18n("Alien Thunder is free and stays free. If it saved you from booting into Windows just to change your keyboard colors, a donation keeps it going.")
        }

        Repeater {
            model: page.wallets
            delegate: ColumnLayout {
                required property var modelData
                Layout.alignment: Qt.AlignHCenter
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Heading {
                    level: 3
                    text: modelData.name
                    Layout.alignment: Qt.AlignHCenter
                }
                QQC2.Label {
                    visible: modelData.networks !== ""
                    text: modelData.networks
                    opacity: 0.7
                    wrapMode: Text.Wrap
                    horizontalAlignment: Text.AlignHCenter
                    Layout.maximumWidth: Kirigami.Units.gridUnit * 24
                    Layout.alignment: Qt.AlignHCenter
                }
                Image {
                    source: Qt.resolvedUrl(modelData.qr)
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 10
                    Layout.preferredHeight: Kirigami.Units.gridUnit * 10
                    Layout.alignment: Qt.AlignHCenter
                    fillMode: Image.PreserveAspectFit
                    smooth: false
                }
                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    QQC2.TextField {
                        text: modelData.address
                        readOnly: true
                        selectByMouse: true
                        font.family: "monospace"
                        Layout.preferredWidth: Kirigami.Units.gridUnit * 22
                    }
                    QQC2.Button {
                        id: copy
                        icon.name: "edit-copy"
                        text: i18n("Copy")
                        onClicked: {
                            clipboard.text = modelData.address
                            clipboard.selectAll()
                            clipboard.copy()
                            copy.text = i18n("Copied")
                            restore.restart()
                        }
                        Timer {
                            id: restore
                            interval: 2000
                            onTriggered: copy.text = i18n("Copy")
                        }
                    }
                }
            }
        }
    }
}
