package com.teleboost.camera.stitch

import android.app.Activity
import android.content.Intent
import com.teleboost.camera.stitch.core.StitchCameraBridge
import com.teleboost.camera.stitch.ui.StitchCameraScreen

/**
 * 主相机 Activity 到接片模块的桥接。
 *
 * 主相机（光·边界主工程）调用此接口进入接片模式。
 * 当前 POC 实现中直接启动 StitchCameraScreen。
 */
object MainActivityBridge {
    /**
     * 从主相机的 Context 打开接片模式。
     */
    fun openStitchFlow(activity: Activity, cameraBridge: StitchCameraBridge) {
        val intent = Intent(activity, StitchCameraScreen::class.java)
        activity.startActivity(intent)
    }
}
