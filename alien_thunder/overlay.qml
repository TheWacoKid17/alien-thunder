import QtQuick
import QtQuick.Window
import QtQml

// The bar stays put while it's dragged: the pointer is measured against it, and moving
// it under the pointer made those measurements chase themselves. It dims while the
// button is down and jumps to where it's let go. Separate see-through windows that
// followed the pointer were tried; kept mapped between drags they crashed Qt about
// once a minute (a repaint landing on a surface KWin had dropped).
QtObject {
    id: root
    required property var backend

    property bool dragging: false
    property real dropX: 0  // where the bar's top-left corner would land, in desktop coordinates
    property real dropY: 0

    property Window bar: BarWindow {
        overlay: root
        backend: root.backend
    }

}
