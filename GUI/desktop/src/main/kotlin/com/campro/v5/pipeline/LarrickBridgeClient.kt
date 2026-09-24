package com.campro.v5.pipeline

import com.campro.v5.utils.SimpleJsonUtils
import org.slf4j.LoggerFactory
import java.nio.file.Files
import java.nio.file.Path
import java.util.UUID
import java.util.concurrent.TimeUnit

/**
 * Shared process-boundary bridge for Larrick GUI adapters.
 *
 * Intended behavior:
 * - Keep all Python subprocess invocation logic in one place.
 * - Use a stable JSON file contract (`--input`, `--output`, `--output-dir`).
 * - Allow mode-specific calls (`optimize`, `orchestrate`, `simulate`, etc.).
 *
 * Current behavior:
 * - Resolves python executable and bridge script from properties/env with
 *   deterministic fallbacks ([BridgeInvocation]).
 * - Subprocess cwd is the Larrick_multi repo root when possible (see CLI contract).
 * - Returns parsed JSON response maps for adapter-level typing.
 */
class LarrickBridgeClient {
    private val logger = LoggerFactory.getLogger(LarrickBridgeClient::class.java)

    /**
     * Execute one bridge mode and return parsed JSON output.
     */
    fun runMode(
        mode: String,
        payload: Map<String, Any>,
        outputDir: Path,
        allowReal: Boolean = false,
    ): Map<String, Any> {
        Files.createDirectories(outputDir)
        val requestId = UUID.randomUUID().toString().take(8)
        val inputFile = outputDir.resolve("gui_bridge_input_${mode}_$requestId.json")
        val outputFile = outputDir.resolve("gui_bridge_output_${mode}_$requestId.json")

        SimpleJsonUtils.writeJsonFile(payload, inputFile)
        val scriptPath = BridgeInvocation.resolveBridgeScriptPath(null, legacyCli = false)
        val workDir = BridgeInvocation.resolveWorkingDirectory(legacyCli = false, resolvedScriptPath = scriptPath)
        val command = buildCommand(mode, inputFile, outputFile, outputDir, allowReal, scriptPath)
        logger.debug("Running bridge command: ${command.joinToString(" ")}")

        val timeoutSec = BridgeInvocation.resolveTimeoutSeconds()
        val process = ProcessBuilder(command)
            .directory(workDir)
            .start()
        val finished = process.waitFor(timeoutSec, TimeUnit.SECONDS)
        if (!finished) {
            process.destroyForcibly()
            return mapOf(
                "status" to "failed",
                "mode" to mode,
                "backend" to "larrick-bridge-client",
                "error" to "Bridge command timed out",
            )
        }

        val stdout = process.inputStream.bufferedReader().use { it.readText() }.trim()
        val stderr = process.errorStream.bufferedReader().use { it.readText() }.trim()
        if (stdout.isNotEmpty()) {
            logger.debug("Bridge stdout: $stdout")
        }
        if (stderr.isNotEmpty()) {
            logger.debug("Bridge stderr: $stderr")
        }

        if (!outputFile.toFile().exists()) {
            return mapOf(
                "status" to "failed",
                "mode" to mode,
                "backend" to "larrick-bridge-client",
                "error" to "Bridge output file missing",
            )
        }
        return SimpleJsonUtils.readJsonFile(outputFile)
    }

    private fun buildCommand(
        mode: String,
        inputFile: Path,
        outputFile: Path,
        outputDir: Path,
        allowReal: Boolean,
        scriptPath: String,
    ): List<String> {
        val pythonExe = BridgeInvocation.resolvePythonExecutable()
        val command = mutableListOf(
            pythonExe,
            scriptPath,
            "--mode",
            mode,
            "--input",
            inputFile.toString(),
            "--output",
            outputFile.toString(),
            "--output-dir",
            outputDir.toString(),
        )
        if (allowReal) {
            command.add("--real")
        }
        return command
    }
}
