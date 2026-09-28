package org.methodmeshenger.app

import android.app.Activity
import android.os.Bundle
import android.graphics.Color
import android.graphics.Typeface
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import org.methodmeshenger.secure.UsbNodeTransport

class MainActivity : Activity() {
    private lateinit var status: TextView
    private lateinit var usbTransport: UsbNodeTransport

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        usbTransport = UsbNodeTransport(this) { line ->
            runOnUiThread { status.text = "Node replied: $line" }
        }
        setContentView(buildScreen())
    }

    private fun buildScreen(): View {
        val background = Color.rgb(247, 243, 240)
        val teal = Color.rgb(68, 127, 123)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 40, 32, 24)
            setBackgroundColor(background)
        }

        root.addView(TextView(this).apply {
            text = "MethodMeshenger"
            textSize = 30f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.rgb(42, 42, 42))
        })
        root.addView(TextView(this).apply {
            text = "Private messages over your own ESP-NOW nodes"
            textSize = 16f
            setTextColor(Color.DKGRAY)
            setPadding(0, 8, 0, 28)
        })

        val nodeCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 20, 24, 20)
            setBackgroundColor(Color.WHITE)
        }
        nodeCard.addView(TextView(this).apply {
            text = "NODE CONNECTION"
            textSize = 13f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(teal)
        })
        status = TextView(this).apply {
            text = "No node connected"
            textSize = 18f
            setTextColor(Color.rgb(42, 42, 42))
            setPadding(0, 10, 0, 16)
        }
        nodeCard.addView(status)
        nodeCard.addView(Button(this).apply {
            text = "Scan USB nodes"
            setOnClickListener {
                val devices = usbTransport.devices()
                status.text = if (devices.isEmpty()) {
                    "No USB node found — connect an ESP board with an OTG adapter"
                } else {
                    "Found ${devices.size} USB node(s); permission pairing is next"
                }
            }
        })
        root.addView(nodeCard, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = 24 })

        root.addView(TextView(this).apply {
            text = "CONVERSATIONS"
            textSize = 13f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(teal)
        })
        root.addView(TextView(this).apply {
            text = "No conversations yet\nConnect a node to start sending messages off-grid."
            textSize = 17f
            gravity = Gravity.CENTER
            setTextColor(Color.DKGRAY)
            setPadding(0, 64, 0, 0)
        }, LinearLayout.LayoutParams(-1, 0, 1f))

        return root
    }

    override fun onDestroy() {
        usbTransport.close()
        super.onDestroy()
    }
}
