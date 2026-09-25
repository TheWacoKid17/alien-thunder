import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    property alias cfg_panel_cpu_temp: cpuTemp.checked
    property alias cfg_panel_gpu_temp: gpuTemp.checked
    property alias cfg_panel_cpu_fan: cpuFan.checked
    property alias cfg_panel_gpu_fan: gpuFan.checked
    property alias cfg_panel_ram: ram.checked
    property bool cfg_panel_cpu_tempDefault
    property bool cfg_panel_gpu_tempDefault
    property bool cfg_panel_cpu_fanDefault
    property bool cfg_panel_gpu_fanDefault
    property bool cfg_panel_ramDefault

    Kirigami.FormLayout {
        QQC2.CheckBox { id: cpuTemp; Kirigami.FormData.label: i18n("Show on the panel:"); text: i18n("CPU temperature") }
        QQC2.CheckBox { id: gpuTemp; text: i18n("GPU temperature") }
        QQC2.CheckBox { id: cpuFan; text: i18n("CPU fan speed") }
        QQC2.CheckBox { id: gpuFan; text: i18n("GPU fan speed") }
        QQC2.CheckBox { id: ram; text: i18n("Memory in use") }
    }
}
