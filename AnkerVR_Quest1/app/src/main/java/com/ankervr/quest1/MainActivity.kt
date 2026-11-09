package com.ankervr.quest1

import android.app.Activity
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.graphics.Color
import android.view.Gravity
import android.content.pm.ActivityInfo

/**
 * AnkerVR Quest 1 starter shell.
 *
 * This is a headset-side UI prototype only. It does NOT yet implement
 * ALVR's streaming protocol, OpenXR tracking transport, or controller input.
 * Those require integrating/building the ALVR client engine.
 */
class MainActivity : Activity() {
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        window.decorView.systemUiVisibility = (
            View.SYSTEM_UI_FLAG_FULLSCREEN
                or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_LAYOUT_STABLE
        )

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(48, 32, 48, 32)
            setBackgroundColor(Color.rgb(10, 16, 29))
        }

        val title = TextView(this).apply {
            text = "ANKERVR"
            textSize = 34f
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
        }
        val subtitle = TextView(this).apply {
            text = "PC VR • META QUEST 1"
            textSize = 16f
            setTextColor(Color.rgb(90, 200, 255))
            gravity = Gravity.CENTER
        }
        status = TextView(this).apply {
            text = "État : interface démarrée\nMoteur de streaming : non intégré"
            textSize = 18f
            setTextColor(Color.LTGRAY)
            gravity = Gravity.CENTER
            setPadding(0, 36, 0, 36)
        }
        val info = TextView(this).apply {
            text = "Cette version est une base de démarrage. Elle n'affiche pas encore le jeu PC.\n\nPour jouer en PCVR, il faut intégrer le client ALVR et son moteur OpenXR."
            textSize = 15f
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
        }
        val button = Button(this).apply {
            text = "Vérifier l'application"
            setOnClickListener {
                status.text = "État : AnkerVR fonctionne sur Android.\nStreaming PC : en attente du moteur ALVR."
            }
        }

        root.addView(title)
        root.addView(subtitle)
        root.addView(status)
        root.addView(info)
        root.addView(button)
        setContentView(root)
    }
}
