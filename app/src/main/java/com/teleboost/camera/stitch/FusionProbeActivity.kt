package com.teleboost.camera.stitch

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Environment
import android.widget.Button
import android.widget.FrameLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.teleboost.camera.R
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.teleboost.camera.stitch.core.MultiCamCaptureBridge
import java.io.File

/**
 * Stage 27 双摄融合 Probe Activity
 */
class FusionProbeActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private lateinit var captureButton: Button
    private lateinit var previewContainer: FrameLayout
    private lateinit var cameraBridge: MultiCamCaptureBridge

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_probe)

        statusText = findViewById(R.id.statusText)
        captureButton = findViewById(R.id.captureButton)
        previewContainer = findViewById(R.id.previewContainer)

        val outputDir = File(
            getExternalFilesDir(Environment.DIRECTORY_PICTURES),
            "Stage27"
        )

        cameraBridge = MultiCamCaptureBridge(this)
        cameraBridge.onStatusUpdate = { msg ->
            runOnUiThread { statusText.text = msg }
        }
        cameraBridge.onError = { msg ->
            runOnUiThread {
                statusText.text = "错误: $msg"
                Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
            }
        }
        cameraBridge.onCaptureComplete = { file ->
            runOnUiThread {
                statusText.text = "融合完成: ${file.parentFile?.name}"
                captureButton.isEnabled = true
            }
        }

        // 初始化 libcp
        if (!cameraBridge.initLibCp()) {
            statusText.text = "libcp 初始化失败"
        }

        captureButton.setOnClickListener {
            captureButton.isEnabled = false
            statusText.text = "拍照中..."
            val sessionDir = File(outputDir, "fusion_${System.currentTimeMillis()}")
            sessionDir.mkdirs()
            cameraBridge.captureFused(sessionDir)
        }

        checkPermissions()
    }

    private fun checkPermissions() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.CAMERA, Manifest.permission.WRITE_EXTERNAL_STORAGE),
                100
            )
        } else {
            startCamera()
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 100) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startCamera()
            } else {
                statusText.text = "需要相机权限"
            }
        }
    }

    private fun startCamera() {
        previewContainer.post {
            previewContainer.post {
            cameraBridge.startPreview(previewContainer)
            captureButton.isEnabled = true
        }
            captureButton.isEnabled = true
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraBridge.release()
    }
}
