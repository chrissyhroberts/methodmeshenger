package org.methodmeshenger.app

import android.app.Activity
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbManager
import android.os.Build
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
    private companion object {
        const val ACTION_USB_PERMISSION = "org.methodmeshenger.app.USB_PERMISSION"
    }

    private lateinit var status: TextView
    private lateinit var usbTransport: UsbNodeTransport
    private var pendingUsbDeviceName: String? = null
    private val usbPermissionReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action != ACTION_USB_PERMISSION) return
            val broadcastDevice = if (Build.VERSION.SDK_INT >= 33) {
                intent.getParcelableExtra(UsbManager.EXTRA_DEVICE, UsbDevice::class.java)
            } else {
                @Suppress("DEPRECATION")
                intent.getParcelableExtra(UsbManager.EXTRA_DEVICE)
            }
            val manager = getSystemService(Context.USB_SERVICE) as UsbManager
            val device = broadcastDevice ?: pendingUsbDeviceName?.let { manager.deviceList[it] }
            val broadcastGranted = intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false)
            val managerGranted = device != null && manager.hasPermission(device)
            val granted = broadcastGranted || managerGranted
            if (device == null || !granted) {
                status.text = "USB permission failed (device=${device != null}, result=$broadcastGranted)"
                return
            }
            status.text = if (usbTransport.connect(device)) {
                "USB node connected"
            } else {
                "USB node could not be opened"
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        usbTransport = UsbNodeTransport(this) { line ->
            runOnUiThread { status.text = "Node replied: $line" }
        }
        val filter = IntentFilter(ACTION_USB_PERMISSION)
        if (Build.VERSION.SDK_INT >= 33) {
            // The USB manager delivers the permission result from the system
            // process, so this dynamic receiver must accept system broadcasts.
            registerReceiver(usbPermissionReceiver, filter, Context.RECEIVER_EXPORTED)
        } else {
            @Suppress("DEPRECATION")
            registerReceiver(usbPermissionReceiver, filter)
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
                    requestUsbPermission(devices.first())
                    "Requesting USB permission for ${devices.first().deviceName}"
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

    private fun requestUsbPermission(device: UsbDevice) {
        pendingUsbDeviceName = device.deviceName
        val intent = PendingIntent.getBroadcast(
            this,
            0,
            Intent(ACTION_USB_PERMISSION),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val manager = getSystemService(Context.USB_SERVICE) as UsbManager
        if (manager.hasPermission(device)) {
            if (usbTransport.connect(device)) status.text = "USB node connected"
            return
        }
        manager.requestPermission(device, intent)
    }

    override fun onDestroy() {
        usbTransport.close()
        unregisterReceiver(usbPermissionReceiver)
        super.onDestroy()
    }
}
