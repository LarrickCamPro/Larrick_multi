package com.campro.v5.pipeline

import java.io.File
import java.nio.file.Files
import java.nio.file.Path

/**
 * Shared resolution for Python bridge subprocesses: working directory, script path,
 * interpreter, and timeout. Keeps [LarrickBridgeClient] and [UnifiedOptimizationBridge]
 * aligned with the Larrick agent CLI contract (LARRICK_MULTI_ROOT, repo-relative `outputs/`).
 */
object BridgeInvocation {
    const val DEFAULT_TIMEOUT_SECONDS: Long = 45L

    /** Optional JVM override for bridge wait timeout (seconds). */
    const val TIMEOUT_PROP: String = "larrick.gui.bridgeTimeoutSeconds"

    const val PYTHON_EXE_PROP: String = "larrick.gui.pythonExe"
    const val PYTHON_EXE_ENV: String = "LARRICK_GUI_PYTHON_EXE"
    const val BRIDGE_SCRIPT_PROP: String = "larrick.gui.bridgeScript"
    const val BRIDGE_SCRIPT_ENV: String = "LARRICK_GUI_BRIDGE_SCRIPT"
    const val LARRICK_ROOT_ENV: String = "LARRICK_MULTI_ROOT"

    private const val LEGACY_SCRIPT_PATH: String = "../scripts/kotlin_bridge_cli.py"

    fun resolveTimeoutSeconds(): Long {
        val prop = System.getProperty(TIMEOUT_PROP)?.trim().orEmpty()
        if (prop.isNotEmpty()) {
            return prop.toLongOrNull() ?: DEFAULT_TIMEOUT_SECONDS
        }
        return DEFAULT_TIMEOUT_SECONDS
    }

    fun resolvePythonExecutable(): String {
        val property = System.getProperty(PYTHON_EXE_PROP)?.trim().orEmpty()
        if (property.isNotEmpty()) return property
        val env = System.getenv(PYTHON_EXE_ENV)?.trim().orEmpty()
        if (env.isNotEmpty()) return env
        return "python3"
    }

    /**
     * Resolve path to `larrick_gui_bridge.py` (or legacy CLI) for argv.
     *
     * @param scriptOverride If non-null/non-blank, used as-is.
     * @param legacyCli If true, returns legacy relative path to kotlin bridge (cwd-sensitive).
     */
    fun resolveBridgeScriptPath(
        scriptOverride: String?,
        legacyCli: Boolean,
    ): String {
        if (!scriptOverride.isNullOrBlank()) return scriptOverride
        if (legacyCli) return LEGACY_SCRIPT_PATH
        val property = System.getProperty(BRIDGE_SCRIPT_PROP)?.trim().orEmpty()
        if (property.isNotEmpty()) return property
        val env = System.getenv(BRIDGE_SCRIPT_ENV)?.trim().orEmpty()
        if (env.isNotEmpty()) return env

        val userDir = Path.of(System.getProperty("user.dir")).normalize()
        val candidates = mutableListOf<Path>()
        System.getenv(LARRICK_ROOT_ENV)?.let { root ->
            candidates.add(Path.of(root).resolve("scripts/larrick_gui_bridge.py"))
        }
        candidates.add(userDir.resolve("../../scripts/larrick_gui_bridge.py").normalize())
        candidates.add(userDir.resolve("../scripts/larrick_gui_bridge.py").normalize())
        candidates.add(userDir.resolve("scripts/larrick_gui_bridge.py").normalize())

        val existing = candidates.firstOrNull { it.toFile().exists() }
        return (existing ?: candidates.first()).toString()
    }

    /**
     * Working directory for the bridge subprocess so Python sees the same repo root as
     * `uv run` / docs (`LARRICK_MULTI_ROOT` or parent of `scripts/larrick_gui_bridge.py`).
     *
     * Legacy CLI mode keeps JVM `user.dir` because paths are relative to the GUI launch cwd.
     */
    fun resolveWorkingDirectory(
        legacyCli: Boolean,
        resolvedScriptPath: String,
    ): File = resolveWorkingDirectoryInternal(
        legacyCli = legacyCli,
        resolvedScriptPath = resolvedScriptPath,
        larrickMultiRootEnv = System.getenv(LARRICK_ROOT_ENV),
        userDir = Path.of(System.getProperty("user.dir")).normalize(),
    )

    internal fun resolveWorkingDirectoryInternal(
        legacyCli: Boolean,
        resolvedScriptPath: String,
        larrickMultiRootEnv: String?,
        userDir: Path,
    ): File {
        if (legacyCli) {
            return File(userDir.toString())
        }
        val rootFromEnv = larrickMultiRootEnv?.trim().orEmpty()
        if (rootFromEnv.isNotEmpty()) {
            val f = File(rootFromEnv)
            if (f.isDirectory) return f
        }
        val scriptPath = Path.of(resolvedScriptPath)
        val normalized: Path = if (scriptPath.isAbsolute) {
            scriptPath.normalize()
        } else {
            userDir.resolve(scriptPath).normalize()
        }
        if (normalized.fileName.toString() == "larrick_gui_bridge.py" && Files.isRegularFile(normalized)) {
            val repoRoot = normalized.parent.parent
            if (Files.isDirectory(repoRoot)) {
                return repoRoot.toFile()
            }
        }
        return File(userDir.toString())
    }

    /**
     * Whether bridge output JSON indicates a successful run per CLI contract (read `status`,
     * not process exit code — [larrick_gui_bridge.py] exits 0 even when status is `failed`).
     */
    fun bridgeOutputIndicatesSuccess(payload: Map<String, Any>): Boolean {
        val status = payload["status"] as? String ?: return false
        return status == "success"
    }
}
