package com.teleboost.camera.stitch.export

class ExportManager {
    fun saveToAlbum(result: Any): String = "saved-to-album"
    fun saveToFolder(result: Any, path: String): String = "$path/saved-result.jpeg"
    fun share(result: Any): String = "shared"
    fun writeExif(result: Any): String = "exif-written"
}
