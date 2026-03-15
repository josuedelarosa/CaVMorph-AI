import { spawn, spawnSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const desktopDir = path.resolve(scriptDir, '..')
const tauriCliPath = path.join(desktopDir, 'node_modules', '@tauri-apps', 'cli', 'tauri.js')
const args = process.argv.slice(2)

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
  const productName = config.package?.productName ?? 'PhenoAI'
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
  const stagingDir = fs.mkdtempSync(path.join(os.tmpdir(), 'phenoai-dmg-'))

  console.error('Tauri hit a macOS DMG unmount error. Falling back to a plain DMG layout.')

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

async function main() {
  if (!fs.existsSync(tauriCliPath)) {
    console.error(`Tauri CLI not found at ${tauriCliPath}`)
    process.exit(1)
  }

  const tauriResult = await runLogged(process.execPath, [tauriCliPath, ...args])

  if (tauriResult.code === 0) {
    process.exit(0)
  }

  const combinedOutput = `${tauriResult.stdout}\n${tauriResult.stderr}`
  const shouldFallback =
    process.platform === 'darwin' &&
    args[0] === 'build' &&
    /error running bundle_dmg\.sh/iu.test(combinedOutput)

  if (!shouldFallback) {
    process.exit(tauriResult.code)
  }

  try {
    await createManualDmg(args)
    process.exit(0)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    console.error(message)
    process.exit(tauriResult.code)
  }
}

await main()