#!/usr/bin/env python3
"""patch-carplay.py

把 CarPlay 歌词视频流最小实验注入到 Capacitor iOS 工程：
  1. 复制 CarPlaySceneDelegate.swift 到 App 目录；
  2. 修改 project.pbxproj 添加该文件的编译引用（Sources build phase）；
  3. 修改 Info.plist 注册 CPTemplateApplicationScene（CarPlay 场景）；
  4. 生成 CarPlay.entitlements（com.apple.developer.carplay-audio，供 ldid 签名）。

用法（在 folia--ios 的 shell 目录内执行）：
  python3 ../inject/patch-carplay.py ios/App/App
"""
import os
import re
import shutil
import sys
import uuid
import plistlib

APP_DIR = sys.argv[1] if len(sys.argv) > 1 else 'ios/App/App'
IOS_APP_ROOT = os.path.dirname(APP_DIR)  # Capacitor 工程根：ios/App
PBX = os.path.join(IOS_APP_ROOT, 'App.xcodeproj', 'project.pbxproj')
INFO = os.path.join(APP_DIR, 'Info.plist')
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'CarPlaySceneDelegate.swift')
DEST = os.path.join(APP_DIR, 'CarPlaySceneDelegate.swift')


def new_id():
    return uuid.uuid4().hex[:24].upper()


# 1. 复制 Swift 文件
if not os.path.exists(SRC):
    sys.exit('[carplay] 找不到 ' + SRC)
shutil.copyfile(SRC, DEST)
print('[carplay] copied', DEST)

# 2. 修改 project.pbxproj
if not os.path.exists(PBX):
    sys.exit('[carplay] 找不到 ' + PBX)
with open(PBX, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

file_ref_id = new_id()
build_file_id = new_id()

# 2a. 新增 PBXFileReference
file_ref = (
    '\t\t' + file_ref_id + ' /* CarPlaySceneDelegate.swift */ = {isa = PBXFileReference; '
    'fileEncoding = 4; lastKnownFileType = sourcecode.swift; '
    'path = CarPlaySceneDelegate.swift; sourceTree = "<group>"; };\n'
)
content = re.sub(
    r'(\n\t\t[A-F0-9]{24} /\* .*? \*/ = \{isa = PBXFileReference;.*?\};\n)',
    lambda m: m.group(1) + file_ref,
    content,
    count=1,
)

# 2b. 新增 PBXBuildFile
build_file = (
    '\t\t' + build_file_id + ' /* CarPlaySceneDelegate.swift in Sources */ = {isa = PBXBuildFile; '
    'fileRef = ' + file_ref_id + ' /* CarPlaySceneDelegate.swift */; };\n'
)
content = re.sub(
    r'(\n\t\t[A-F0-9]{24} /\* .*? \*/ = \{isa = PBXBuildFile;.*?\};\n)',
    lambda m: m.group(1) + build_file,
    content,
    count=1,
)

# 2c. 加入 Sources build phase
phase_pattern = (
    r'(/\* Sources \*/ = \{\n'
    r'\t\t\tisa = PBXSourcesBuildPhase;\n'
    r'\t\t\tbuildActionMask = 2147483647;\n'
    r'\t\t\tfiles = \(\n)'
    r'(.*?)'
    r'(\n\t\t\t\);)'
)
def sources_repl(m):
    line = '\t\t\t\t' + build_file_id + ' /* CarPlaySceneDelegate.swift in Sources */,\n'
    return m.group(1) + line + m.group(2) + m.group(3)

new_content = re.sub(phase_pattern, sources_repl, content, count=1, flags=re.DOTALL)
if new_content == content:
    sys.exit('[carplay] 未找到 Sources build phase，pbxproj 结构可能变化')
content = new_content

with open(PBX, 'w', encoding='utf-8') as f:
    f.write(content)
print('[carplay] patched project.pbxproj')

# 3. 修改 Info.plist：注册 CarPlay 场景
with open(INFO, 'rb') as f:
    info = plistlib.load(f)

scene_manifest = info.setdefault('UIApplicationSceneManifest', {})
configs = scene_manifest.setdefault('UISceneConfigurations', {})
carplay_role = 'CPTemplateApplicationSceneSessionRoleApplication'
carplay_scenes = configs.setdefault(carplay_role, [])
carplay_scenes.append({
    'UISceneConfigurationName': 'CarPlay',
    'UISceneDelegateClassName': 'CarPlaySceneDelegate',
})
# 去重
configs[carplay_role] = list({tuple(sorted(c.items())): c for c in carplay_scenes}.values())

with open(INFO, 'wb') as f:
    plistlib.dump(info, f)
print('[carplay] Info.plist registered CarPlay scene')

# 4. 生成 entitlements（供 ldid 签名注入）
ent_path = os.path.join(APP_DIR, 'CarPlay.entitlements')
with open(ent_path, 'wb') as f:
    plistlib.dump({'com.apple.developer.carplay-audio': True}, f)
print('[carplay] entitlements ->', ent_path)