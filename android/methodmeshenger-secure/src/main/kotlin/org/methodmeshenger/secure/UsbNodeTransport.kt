package org.methodmeshenger.secure

import android.content.Context
import android.hardware.usb.UsbConstants
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbDeviceConnection
import android.hardware.usb.UsbEndpoint
import android.hardware.usb.UsbInterface
import android.hardware.usb.UsbManager
import java.nio.charset.StandardCharsets
import java.util.concurrent.atomic.AtomicBoolean

/** Minimal USB-CDC/bulk transport for the serial-first ESP firmware. */
class UsbNodeTransport(context: Context, private val onLine: (String) -> Unit) {
    private val usbManager = context.getSystemService(Context.USB_SERVICE) as UsbManager
    private var connection: UsbDeviceConnection? = null
    private var input: UsbEndpoint? = null
    private var output: UsbEndpoint? = null
    private var selectedInterface: UsbInterface? = null
    private val running = AtomicBoolean(false)

    fun devices(): List<UsbDevice> = usbManager.deviceList.values.toList()

    fun connect(device: UsbDevice): Boolean {
        close()
        if (!usbManager.hasPermission(device)) return false
        val selected = findBulkEndpoints(device) ?: return false
        val opened = usbManager.openDevice(device) ?: return false
        if (!opened.claimInterface(selected.usbInterface, true)) {
            opened.close()
            return false
        }
        connection = opened
        selectedInterface = selected.usbInterface
        input = selected.input
        output = selected.output
        running.set(true)
        Thread(::readLoop, "methodmeshenger-usb-read").apply {
            isDaemon = true
            start()
        }
        return true
    }

    fun sendLine(line: String): Boolean {
        val current = connection ?: return false
        val endpoint = output ?: return false
        val bytes = (line.trimEnd() + "\n").toByteArray(StandardCharsets.UTF_8)
        return current.bulkTransfer(endpoint, bytes, bytes.size, 2_000) == bytes.size
    }

    fun close() {
        running.set(false)
        connection?.let { current ->
            selectedInterface?.let { current.releaseInterface(it) }
            current.close()
        }
        connection = null
        selectedInterface = null
        input = null
        output = null
    }

    private fun readLoop() {
        val buffer = ByteArray(512)
        val pending = StringBuilder()
        while (running.get()) {
            val current = connection ?: break
            val endpoint = input ?: break
            val count = current.bulkTransfer(endpoint, buffer, buffer.size, 250)
            if (count <= 0) continue
            pending.append(String(buffer, 0, count, StandardCharsets.UTF_8))
            while (true) {
                val newline = pending.indexOf("\n")
                if (newline < 0) break
                val line = pending.substring(0, newline).trim()
                pending.delete(0, newline + 1)
                if (line.isNotEmpty()) onLine(line)
            }
        }
    }

    private data class BulkEndpoints(
        val usbInterface: UsbInterface,
        val input: UsbEndpoint,
        val output: UsbEndpoint,
    )

    private fun findBulkEndpoints(device: UsbDevice): BulkEndpoints? {
        for (index in 0 until device.interfaceCount) {
            val usbInterface = device.getInterface(index)
            var inEndpoint: UsbEndpoint? = null
            var outEndpoint: UsbEndpoint? = null
            for (endpointIndex in 0 until usbInterface.endpointCount) {
                val endpoint = usbInterface.getEndpoint(endpointIndex)
                if (endpoint.type != UsbConstants.USB_ENDPOINT_XFER_BULK) continue
                if (endpoint.direction == UsbConstants.USB_DIR_IN) inEndpoint = endpoint
                if (endpoint.direction == UsbConstants.USB_DIR_OUT) outEndpoint = endpoint
            }
            if (inEndpoint != null && outEndpoint != null) return BulkEndpoints(usbInterface, inEndpoint, outEndpoint)
        }
        return null
    }
}
