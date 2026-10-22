# 节律控制 GitHub 更新接入

本包只是待上传文件，生成过程不会访问账号、发布或删除远程资源。
目标仓库固定为 cofearis/claude-todo，默认分支 master。应用查询公开 GitHub Releases，不需要账号或 Token。

## 第一次启用

1. 在仓库中将只有空行的 rhythm_control 占位文件替换为同名文件夹。
2. 将包里的 .github/workflows/rhythm-release.yml 放到仓库根目录的对应位置，rhythm_control 文件夹同样合并到根目录。保留其他文件和工作流。
3. 确认 Actions 已启用、工作流获 contents:write 权限。工作流只使用 GitHub 内置临时令牌，APK 内不含发布令牌。
4. 提交后，由 rhythm_control/release.json 的更改触发发布；也可以在 Actions 中手动运行 Publish rhythm control。
5. 确认生成 rhythm_control-v0.6.3 Release，附件包括 APK 和 rhythm-update.json。首次完成后，0.6.3 内检查更新应提示已是最新版本。

## 后续版本

使用每个新版工程生成的 github_publish_版本号.zip，以新 APK 和 release.json 替换 rhythm_control 中对应文件。
版本号和 versionCode 都必须递增，沿用相同应用签名。旧的仓库工作目录 APK 可以在提交时移除，Git 历史保留；工作流自动清理的是 Release 及附件，不重写 Git 历史。
文件夹内只需保留待发布的一套 APK/元信息，用户下载入口是 Releases。

流程先校验本地大小/SHA-256，再创建草稿、上传完整附件，最后发布；失败上传保留草稿供检查，不删除任何旧版。
发布成功后只对 rhythm_control-v数字.数字.数字 标签且同时带有标准 APK/元信息附件的正式版本排序，保留最高五版，删除更早的 Release（包括其附件），不删除 Git 标签。其他项目、草稿和预发布不参与清理。
同版相同元信息的重试只进行保留清理，不覆盖 APK；不同内容同版本会拒绝。若出现未完成草稿，检查处理草稿后再运行。

## 应用侧

关于页点击蓝色“检查更新”。检查期间显示“检查中..”；失败明确提示，恢复后可重试。没有任何专属发布时按本版约定提示“已是最新版本”；网络或更新信息出错仍提示错误并可重试。
有新版本时点击下载文字；任务未结束（含暂停、准备、采集、收尾）则拦截下载和安装。
下载、哈希及包名/版本/签名校验都在后台执行。完成时若关于页处于前台且任务空闲，打开安卓安装许可/确认；后台完成则保留“下载完成，点击安装”，不会强行弹窗。
首次允许“安装未知应用”后返回，重新点击安装。系统仍可能额外要求安装确认。
应用退出取消本次检查/下载，不保留半包；网络超时、校验失败均可重试。没有自动检查、自动安装或开机联网。

注意：只把 github_publish 包上传到公开仓库，不要上传源码包内的 runtime/debug.keystore 或本地缓存。

参考：
- https://docs.github.com/en/rest/releases/releases
- https://docs.github.com/en/rest/releases/assets
- https://developer.android.com/reference/android/content/pm/PackageManager#canRequestPackageInstalls()
