import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    property alias cfg_panel_cpu_temp: panelCpuTemp.checked
    property alias cfg_panel_cpu_load: panelCpuLoad.checked
    property alias cfg_panel_gpu_temp: panelGpuTemp.checked
    property alias cfg_panel_gpu_mem: panelGpuMem.checked
    property alias cfg_panel_cpu_fan: panelCpuFan.checked
    property alias cfg_panel_gpu_fan: panelGpuFan.checked
    property alias cfg_panel_ram: panelRam.checked
    property alias cfg_panel_ram_gb: panelRamGb.checked
    property alias cfg_overlay_cpu_temp: overlayCpuTemp.checked
    property alias cfg_overlay_cpu_load: overlayCpuLoad.checked
    property alias cfg_overlay_gpu_temp: overlayGpuTemp.checked
    property alias cfg_overlay_gpu_mem: overlayGpuMem.checked
    property alias cfg_overlay_cpu_fan: overlayCpuFan.checked
    property alias cfg_overlay_gpu_fan: overlayGpuFan.checked
    property alias cfg_overlay_ram: overlayRam.checked
    property alias cfg_overlay_ram_gb: overlayRamGb.checked
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

    Kirigami.FormLayout {
        QQC2.CheckBox { id: panelCpuTemp; Kirigami.FormData.label: i18n("Show on the panel:"); text: i18n("CPU temperature") }
        QQC2.CheckBox { id: panelCpuLoad; text: i18n("CPU load") }
        QQC2.CheckBox { id: panelGpuTemp; text: i18n("GPU temperature") }
        QQC2.CheckBox { id: panelGpuMem; text: i18n("GPU memory (VRAM) in use") }
        QQC2.CheckBox { id: panelCpuFan; text: i18n("CPU fan speed") }
        QQC2.CheckBox { id: panelGpuFan; text: i18n("GPU fan speed") }
        QQC2.CheckBox { id: panelRam; text: i18n("Memory in use") }
        QQC2.CheckBox { id: panelRamGb; text: i18n("Memory in use, in GB") }

        Item { Kirigami.FormData.isSection: true }

        QQC2.CheckBox { id: overlayCpuTemp; Kirigami.FormData.label: i18n("Show in the overlay:"); text: i18n("CPU temperature") }
        QQC2.CheckBox { id: overlayCpuLoad; text: i18n("CPU load") }
        QQC2.CheckBox { id: overlayGpuTemp; text: i18n("GPU temperature") }
        QQC2.CheckBox { id: overlayGpuMem; text: i18n("GPU memory (VRAM) in use") }
        QQC2.CheckBox { id: overlayCpuFan; text: i18n("CPU fan speed") }
        QQC2.CheckBox { id: overlayGpuFan; text: i18n("GPU fan speed") }
        QQC2.CheckBox { id: overlayRam; text: i18n("Memory in use") }
        QQC2.CheckBox { id: overlayRamGb; text: i18n("Memory in use, in GB") }
    }
}
