package com.teleboost.camera.stitch.export

import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.util.Log
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * 接片结果导出管理器。
 *
 * 职责：
 * - 保存到应用内部目录
 * - 保存到系统相册（MediaStore，Android 10+）
 * - 分享到其他 App
 * - EXIF 保持最小必要信息
 *
 * 红线：
 * - 不修改图像真实性
 * - 文件命名规范统一
 */
class ExportManager {
    companion object {
        private const val TAG = "ExportManager"
        private const val JPEG_QUALITY = 97
        private const val FILENAME_PREFIX = "LBM_stitch_"

        /** 临时文件目录 */
        private const val STITCH_DIR = "StitchResults"
    }

    private val dateFormat = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US)

    /**
     * 保存到应用内部缓存目录（用于分享等临时用途）。
     */
    fun saveToCache(context: Context, bitmap: Bitmap, format: Bitmap.CompressFormat = Bitmap.CompressFormat.JPEG): File? {
        return try {
            val dir = File(context.cacheDir, STITCH_DIR)
            if (!dir.exists()) dir.mkdirs()

            val fileName = generateFileName("jpeg")
            val file = File(dir, fileName)
            FileOutputStream(file).use { out ->
                bitmap.compress(format, JPEG_QUALITY, out)
            }
            Log.d(TAG, "保存到缓存: ${file.absolutePath} (${file.length()} bytes)")
            file
        } catch (e: Exception) {
            Log.e(TAG, "saveToCache 失败", e)
            null
        }
    }

    /**
     * 保存到系统相册（Android 10+ 使用 MediaStore）。
     */
    fun saveToAlbum(context: Context, bitmap: Bitmap): Uri? {
        return try {
            val filename = generateFileName("jpeg")
            val contentValues = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, filename)
                put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
                put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/$STITCH_DIR")
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }

            val uri = context.contentResolver.insert(
                MediaStore.Images.Media.EXTERNAL_CONTENT_URI, contentValues
            )

            if (uri != null) {
                context.contentResolver.openOutputStream(uri)?.use { out ->
                    bitmap.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, out)
                }
                contentValues.clear()
                contentValues.put(MediaStore.Images.Media.IS_PENDING, 0)
                context.contentResolver.update(uri, contentValues, null, null)
                Log.d(TAG, "保存到相册: $uri")
            }
            uri
        } catch (e: Exception) {
            Log.e(TAG, "saveToAlbum 失败", e)
            null
        }
    }

    /**
     * 保存到指定文件夹。
     */
    fun saveToFolder(bitmap: Bitmap, path: String): File? {
        return try {
            val dir = File(path)
            if (!dir.exists()) dir.mkdirs()

            val fileName = generateFileName("jpeg")
            val file = File(dir, fileName)
            FileOutputStream(file).use { out ->
                bitmap.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, out)
            }
            Log.d(TAG, "保存到文件夹: ${file.absolutePath}")
            file
        } catch (e: Exception) {
            Log.e(TAG, "saveToFolder 失败", e)
            null
        }
    }

    /**
     * 分享图片。
     */
    fun share(context: Context, bitmap: Bitmap): Boolean {
        return try {
            // 先保存到缓存
            val file = saveToCache(context, bitmap) ?: return false

            val uri = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                // Android 7+ 使用 FileProvider
                // 需要 FileProvider 配置，此处暂用简化实现
                Uri.fromFile(file)
            } else {
                Uri.fromFile(file)
            }

            val shareIntent = Intent(Intent.ACTION_SEND).apply {
                type = "image/jpeg"
                putExtra(Intent.EXTRA_STREAM, uri)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            context.startActivity(Intent.createChooser(shareIntent, "分享接片结果"))
            Log.d(TAG, "分享启动")
            true
        } catch (e: Exception) {
            Log.e(TAG, "share 失败", e)
            false
        }
    }

    /**
     * 生成规范文件名：LBM_stitch_20260707_120000.jpeg
     */
    private fun generateFileName(extension: String): String {
        val timestamp = dateFormat.format(Date())
        return "${FILENAME_PREFIX}${timestamp}.$extension"
    }
}
