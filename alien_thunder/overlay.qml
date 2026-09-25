import QtQuick
import QtQml

QtObject {
    id: root
    required property var backend

    property Instantiator tiles: Instantiator {
        model: root.backend.items
        delegate: OverlayTile {
            required property string modelData
            item: modelData
            backend: root.backend
        }
    }
}
