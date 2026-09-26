import QtQuick
import QtQuick.Window
import QtQml

// The bar, plus one see-through "ghost" window per screen that shows the bar while it's
// being dragged. The bar itself stays still during a drag: the pointer is measured
// against it, and moving it under the pointer made those measurements chase themselves.
QtObject {
    id: root
    required property var backend

    property bool dragging: false
    property real ghostX: 0  // the dragged bar's top-left corner, in desktop coordinates
    property real ghostY: 0

    property Window bar: BarWindow {
        overlay: root
        backend: root.backend
    }

    property Instantiator ghosts: Instantiator {
        model: root.backend.screens
        delegate: GhostWindow {
            required property var modelData
            screenInfo: modelData
            overlay: root
            backend: root.backend
        }
    }
}
