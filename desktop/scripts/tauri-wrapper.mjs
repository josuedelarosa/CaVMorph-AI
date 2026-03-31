import { spawn, spawnSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const desktopDir = path.resolve(scriptDir, '..')
const repoRoot = path.resolve(desktopDir, '..')
const tauriCliPath = path.join(desktopDir, 'node_modules', '@tauri-apps', 'cli', 'tauri.js')
const args = process.argv.slice(2)
const runtimeDir = path.join(desktopDir, 'runtime', 'python')
const runtimeManifestPath = path.join(runtimeDir, 'runtime_manifest.json')

function runLogged(command, commandArgs, options = {}) {
  const { cwd = desktopDir, env = process.env } = options

  return new Promise((resolve, reject) => {
    const child = spawn(command, commandArgs, {
      cwd,
      env,
      stdio: ['inherit', 'pipe', 'pipe'],
    })

    let stdout = ''
    let stderr = ''

    child.stdout.on('data', (chunk) => {
      const text = chunk.toString()
      stdout += text
      process.stdout.write(text)
    })

    child.stderr.on('data', (chunk) => {
      const text = chunk.toString()
      stderr += text
      process.stderr.write(text)
    })

    child.on('error', reject)
    child.on('close', (code) => {
      resolve({ code: code ?? 1, stdout, stderr })
    })
  })
}

function readTauriConfig() {
  const configPath = path.join(desktopDir, 'src-tauri', 'tauri.conf.json')
  return JSON.parse(fs.readFileSync(configPath, 'utf8'))
}

function resolveTargetPlatform(cliArgs) {
  const targetIndex = cliArgs.findIndex((arg) => arg === '--target')

  if (targetIndex !== -1) {
    const target = cliArgs[targetIndex + 1] ?? ''

    if (target.includes('apple-darwin')) {
      return 'macos'
    }

    if (target.includes('windows')) {
      return 'windows'
    }

    if (target.includes('linux')) {
      return 'linux'
    }
  }

  if (process.platform === 'darwin') {
    return 'macos'
  }

  if (process.platform === 'win32') {
    return 'windows'
  }

  if (process.platform === 'linux') {
    return 'linux'
  }

  throw new Error(`Unsupported build platform: ${process.platform}`)
}

function resolveTargetArch(cliArgs) {
  const targetIndex = cliArgs.findIndex((arg) => arg === '--target')

  if (targetIndex !== -1) {
    const target = cliArgs[targetIndex + 1] ?? ''

    if (target.includes('universal')) {
      throw new Error(
        'Bundled Python runtime packaging does not support universal macOS targets. Build separate arm64 and x64 installers instead.'
      )
    }

    if (target.startsWith('aarch64') || target.includes('arm64')) {
      return 'arm64'
    }

    if (target.startsWith('x86_64') || target.includes('x64')) {
      return 'x64'
    }
  }

  if (process.arch === 'arm64') {
    return 'arm64'
  }

  if (process.arch === 'x64') {
    return 'x64'
  }

  throw new Error(`Unsupported build architecture: ${process.arch}`)
}

function readRuntimeManifest() {
  if (!fs.existsSync(runtimeManifestPath)) {
    return null
  }

  try {
    return JSON.parse(fs.readFileSync(runtimeManifestPath, 'utf8'))
  } catch {
    return null
  }
}

function runtimeExecutableCandidates(osName, baseDir) {
  if (osName === 'windows') {
    return [path.join(baseDir, 'python.exe')]
  }

  return [
    path.join(baseDir, 'bin', 'python3'),
    path.join(baseDir, 'bin', 'python'),
  ]
}

function hasPreparedRuntime(osName, arch) {
  const manifest = readRuntimeManifest()
  if (!manifest) {
    return false
  }

  if (manifest.platform !== osName || manifest.arch !== arch) {
    return false
  }

  return runtimeExecutableCandidates(osName, runtimeDir).some((candidate) => fs.existsSync(candidate))
}

function buildPythonCandidates() {
  const candidates = []

  if (process.env.FISHOMETRICS_BUILD_PYTHON) {
    candidates.push({ command: process.env.FISHOMETRICS_BUILD_PYTHON, args: [] })
  }

  const repoCondaPython = process.platform === 'win32'
    ? path.join(repoRoot, '.conda', 'python.exe')
    : path.join(repoRoot, '.conda', 'bin', 'python')

  if (fs.existsSync(repoCondaPython)) {
    candidates.push({ command: repoCondaPython, args: [] })
  }

  if (process.platform === 'win32') {
    candidates.push({ command: 'py', args: ['-3'] })
  }

  candidates.push({ command: 'python3', args: [] })
  candidates.push({ command: 'python', args: [] })

  return candidates
}

function findWorkingPython() {
  for (const candidate of buildPythonCandidates()) {
    const probe = spawnSync(candidate.command, [...candidate.args, '--version'], {
      cwd: repoRoot,
      encoding: 'utf8',
      stdio: 'pipe',
    })

    if (probe.status === 0) {
      return candidate
    }
  }

  return null
}

async function ensureBundledRuntime(cliArgs) {
  if (cliArgs[0] !== 'build' || process.env.FISHOMETRICS_SKIP_RUNTIME_PREPARE === '1') {
    return
  }

  const osName = resolveTargetPlatform(cliArgs)
  const arch = resolveTargetArch(cliArgs)

  if (hasPreparedRuntime(osName, arch)) {
    console.log(`Using bundled Python runtime from ${runtimeDir}`)
    return
  }

  const python = findWorkingPython()
  if (!python) {
    throw new Error(
      'No build-time Python interpreter was found to prepare the bundled runtime. Set FISHOMETRICS_BUILD_PYTHON or install Python 3.9+ on the build machine.'
    )
  }

  console.log(`Preparing bundled Python runtime for ${osName}/${arch}...`)

  const prepareArgs = [
    ...python.args,
    path.join(repoRoot, 'scripts', 'prepare_runtime.py'),
    '--platform',
    osName,
    '--arch',
    arch,
    '--clean',
  ]
  const result = await runLogged(python.command, prepareArgs, { cwd: repoRoot })

  if (result.code !== 0 || !hasPreparedRuntime(osName, arch)) {
    throw new Error('Failed to prepare the bundled Python runtime')
  }
}

function verifyBundledRuntimeInArtifacts(cliArgs) {
  if (cliArgs[0] !== 'build') {
    return
  }

  const targetPlatform = resolveTargetPlatform(cliArgs)
  const targetArch = resolveTargetArch(cliArgs)
  const config = readTauriConfig()
  const productName = config.package?.productName ?? 'Fishometrics'

  if (targetPlatform === 'macos') {
    const appRuntimeDir = path.join(
      desktopDir,
      'src-tauri',
      'target',
      'release',
      'bundle',
      'macos',
      `${productName}.app`,
      'Contents',
      'Resources',
      '_up_',
      'runtime',
      'python'
    )

    if (!runtimeExecutableCandidates(targetPlatform, appRuntimeDir).some((candidate) => fs.existsSync(candidate))) {
      throw new Error(`Bundled Python runtime missing from app artifact at ${appRuntimeDir}`)
    }

    return
  }

  if (!hasPreparedRuntime(targetPlatform, targetArch)) {
    throw new Error(`Bundled Python runtime missing for ${targetPlatform}/${targetArch}`)
  }
}

function findMachOBinaries(appPath) {
  const dylibs = spawnSync('find', [appPath, '-type', 'f', '(', '-name', '*.dylib', '-o', '-name', '*.so', ')'], {
    encoding: 'utf8',
    stdio: 'pipe',
  })

  const sharedLibs = (dylibs.stdout ?? '').trim().split('\n').filter(Boolean)

  const execFind = spawnSync('find', [
    appPath, '-type', 'f', '-perm', '+0111',
    '-not', '-name', '*.dylib', '-not', '-name', '*.so',
    '-not', '-name', '*.py', '-not', '-name', '*.pyc',
    '-not', '-name', '*.sh', '-not', '-name', '*.js',
  ], { encoding: 'utf8', stdio: 'pipe' })

  const execCandidates = (execFind.stdout ?? '').trim().split('\n').filter(Boolean)
  const execMachO = execCandidates.filter((f) => {
    const probe = spawnSync('file', ['--brief', f], { encoding: 'utf8', stdio: 'pipe' })
    return /Mach-O/.test(probe.stdout ?? '')
  })

  const all = [...sharedLibs, ...execMachO]
  all.sort((a, b) => b.split('/').length - a.split('/').length)
  return all
}

function signAppBundle(appPath) {
  console.log('Signing app bundle with ad-hoc identity...')

  // Copy the bundle to a temp directory to strip filesystem xattrs
  // (com.apple.FinderInfo, fileprovider, etc.) that block codesign.
  const cleanDir = fs.mkdtempSync(path.join(os.tmpdir(), 'fishometrics-sign-'))
  const cleanApp = path.join(cleanDir, path.basename(appPath))

  console.log('  Creating clean copy (stripping xattrs)...')
  const ditto = spawnSync('ditto', ['--norsrc', appPath, cleanApp], {
    encoding: 'utf8',
    stdio: 'pipe',
  })

  if (ditto.status !== 0) {
    fs.rmSync(cleanDir, { recursive: true, force: true })
    throw new Error(`ditto failed: ${(ditto.stderr ?? '').trim()}`)
  }

  const binaries = findMachOBinaries(cleanApp)
  console.log(`  Found ${binaries.length} nested Mach-O binaries to sign`)

  let signed = 0
  for (const binary of binaries) {
    const result = spawnSync('codesign', ['-s', '-', '--force', binary], {
      encoding: 'utf8',
      stdio: 'pipe',
    })

    if (result.status === 0) {
      signed++
    } else {
      console.warn(`  Warning: could not sign ${path.relative(cleanApp, binary)}: ${(result.stderr ?? '').trim()}`)
    }
  }

  console.log(`  Signed ${signed}/${binaries.length} nested binaries`)

  const bundleSign = spawnSync('codesign', ['-s', '-', '--force', cleanApp], {
    encoding: 'utf8',
    stdio: 'pipe',
  })

  if (bundleSign.status !== 0) {
    fs.rmSync(cleanDir, { recursive: true, force: true })
    throw new Error(`Failed to sign app bundle: ${(bundleSign.stderr ?? '').trim()}`)
  }

  const verify = spawnSync('codesign', ['--verify', '--deep', '--strict', cleanApp], {
    encoding: 'utf8',
    stdio: 'pipe',
  })

  if (verify.status !== 0) {
    const loose = spawnSync('codesign', ['--verify', cleanApp], {
      encoding: 'utf8',
      stdio: 'pipe',
    })

    if (loose.status !== 0) {
      fs.rmSync(cleanDir, { recursive: true, force: true })
      throw new Error(`App signature verification failed: ${(verify.stderr ?? '').trim()}`)
    }

    console.warn(`  Warning: --deep --strict verification failed (${(verify.stderr ?? '').trim()}) but basic verification passed`)
  } else {
    console.log('  App bundle signature verified (deep + strict)')
  }

  const info = spawnSync('codesign', ['-dvvv', cleanApp], {
    encoding: 'utf8',
    stdio: 'pipe',
  })

  const sealedMatch = (info.stderr ?? '').match(/Sealed Resources.*?(\S+)/)
  if (sealedMatch && sealedMatch[0].includes('none')) {
    fs.rmSync(cleanDir, { recursive: true, force: true })
    throw new Error('Sealed Resources still shows none after signing')
  }

  // Replace the original with the signed copy
  fs.rmSync(appPath, { recursive: true, force: true })
  fs.renameSync(cleanApp, appPath)
  fs.rmSync(cleanDir, { recursive: true, force: true })

  console.log('  Ad-hoc signing complete')
}

function resolveArchLabel(cliArgs) {
  const targetIndex = cliArgs.findIndex((arg) => arg === '--target')

  if (targetIndex !== -1) {
    const target = cliArgs[targetIndex + 1] ?? ''

    if (target.includes('universal')) {
      return 'universal'
    }

    if (target.startsWith('aarch64')) {
      return 'aarch64'
    }

    if (target.startsWith('x86_64')) {
      return 'x64'
    }
  }

  if (process.arch === 'arm64') {
    return 'aarch64'
  }

  if (process.arch === 'x64') {
    return 'x64'
  }

  return process.arch
}

function resolveDmgName(dmgDir, productName, version, archLabel) {
  if (fs.existsSync(dmgDir)) {
    const rwName = fs
      .readdirSync(dmgDir)
      .find((name) => name.startsWith('rw.') && name.endsWith('.dmg'))

    if (rwName) {
      return rwName.slice(3)
    }
  }

  return `${productName}_${version}_${archLabel}.dmg`
}

function forceDetachVolume(volumeName) {
  const mountPath = path.join('/Volumes', volumeName)
  spawnSync('hdiutil', ['detach', mountPath, '-force'], {
    stdio: 'ignore',
  })
}

async function createManualDmg(cliArgs) {
  const config = readTauriConfig()
  const productName = config.package?.productName ?? 'Fishometrics'
  const version = config.package?.version ?? '0.1.0'
  const bundleDir = path.join(desktopDir, 'src-tauri', 'target', 'release', 'bundle')
  const dmgDir = path.join(bundleDir, 'dmg')
  const appPath = path.join(bundleDir, 'macos', `${productName}.app`)

  if (!fs.existsSync(appPath)) {
    throw new Error(`App bundle not found at ${appPath}`)
  }

  fs.mkdirSync(dmgDir, { recursive: true })

  const dmgName = resolveDmgName(dmgDir, productName, version, resolveArchLabel(cliArgs))
  const outputPath = path.join(dmgDir, dmgName)
  const rwPath = path.join(dmgDir, `rw.${dmgName}`)
  const volumeName = dmgName.replace(/\.dmg$/u, '')
  const stagingDir = fs.mkdtempSync(path.join(os.tmpdir(), 'fishometrics-dmg-'))

  forceDetachVolume(volumeName)
  fs.rmSync(outputPath, { force: true })
  fs.rmSync(rwPath, { force: true })

  try {
    fs.cpSync(appPath, path.join(stagingDir, `${productName}.app`), { recursive: true })
    fs.symlinkSync('/Applications', path.join(stagingDir, 'Applications'))

    const result = await runLogged('hdiutil', [
      'create',
      '-volname',
      productName,
      '-srcfolder',
      stagingDir,
      '-ov',
      '-format',
      'UDZO',
      outputPath,
    ])

    if (result.code !== 0) {
      throw new Error('Manual DMG creation failed')
    }

    if (!fs.existsSync(outputPath)) {
      throw new Error(`Expected DMG not found at ${outputPath}`)
    }

    console.log(`Manual DMG created at ${outputPath}`)
  } finally {
    fs.rmSync(stagingDir, { recursive: true, force: true })
  }
}

function resolveAppPath() {
  const config = readTauriConfig()
  const productName = config.package?.productName ?? 'Fishometrics'
  return path.join(
    desktopDir,
    'src-tauri',
    'target',
    'release',
    'bundle',
    'macos',
    `${productName}.app`
  )
}

async function main() {
  if (!fs.existsSync(tauriCliPath)) {
    console.error(`Tauri CLI not found at ${tauriCliPath}`)
    process.exit(1)
  }

  try {
    await ensureBundledRuntime(args)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    console.error(message)
    process.exit(1)
  }

  const isReleaseBuild = args[0] === 'build'
  const isMacOS = isReleaseBuild && resolveTargetPlatform(args) === 'macos'

  // On macOS, build only the .app bundle (skip Tauri's DMG step).
  // We sign the .app ourselves and create the DMG afterward.
  const tauriArgs = [...args]
  if (isMacOS && !tauriArgs.includes('--bundles') && !tauriArgs.includes('-b')) {
    tauriArgs.push('--bundles', 'app')
  }

  const tauriResult = await runLogged(process.execPath, [tauriCliPath, ...tauriArgs])

  if (tauriResult.code !== 0) {
    process.exit(tauriResult.code)
  }

  if (isMacOS) {
    const appPath = resolveAppPath()
    verifyBundledRuntimeInArtifacts(args)
    signAppBundle(appPath)
    await createManualDmg(args)
  } else {
    verifyBundledRuntimeInArtifacts(args)
  }

  process.exit(0)
}

await main()