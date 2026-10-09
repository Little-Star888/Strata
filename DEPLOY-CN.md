# 国内环境部署手册(deploy/v0.1.41-cn)

这是 Little-Star888 fork 的部署分支,不是上游功能分支。基线:上游 tag
`v0.1.41`(commit fb58e0d)+ 本分支的部署提交。与上游的全部差异:
Dockerfile(apt/pip 清华源、基础镜像换阿里云仓库、sm_120 编译)、
.dockerignore(保留预置的 llama.cpp)、docker-compose.yml、.env.example、
.gitignore(忽略 .env)。

## 日常操作(docker compose,v2 语法,本机 v2.40.3)

```bash
cp .env.example .env          # 首次;之后所有开关都在 .env 里(中文注释)
docker compose up -d          # 应用 .env 的改动(自动重建容器,模型不重下)
docker compose logs -f        # 看下载/加载/报错
docker compose stop           # 停(比如给 ninfer-serve 让显存——两者显存互斥)
```

- unsloth 档(UD-IQ4_XS / UD-Q4_K_XL)要加 `FAMILY=unsloth`;原装档留空。
- 修改已装档位的设置(上下文/Vision/KV/API_KEY)需一次性 `REINSTALL=1`,生效后删掉。
- 端口映射超出 127.0.0.1 必须先设 `API_KEY`(AGENTS.md);`HOST_PORT` 是宿主机
  端口,容器内 8080 固定不动。

## 从零复活(全新机器,约 40 分钟)

前置:Docker + compose v2;NVIDIA 驱动 ≥580 + nvidia-container-toolkit;
宿主机 daemon.json 的 registry-mirrors 已配置(本方案不改它)。
只依赖三个国内通道:gh.kejilion.pro(源码)、用户阿里云仓库(基础镜像)、
daemon.json 加速器(dockerfile 语法前端)。

```bash
# 1. 源码
git clone https://gh.kejilion.pro/https://github.com/Little-Star888/Strata.git
cd Strata && git checkout deploy/v0.1.41-cn

# 2. dockerfile 语法前端(清过构建缓存后也需要;走加速器,秒下)
docker pull docker/dockerfile:1

# 3. 预置 llama.cpp 到固定 commit(38MB;目录名自带 hash 可核对)
curl -LO https://gh.kejilion.pro/https://github.com/ggml-org/llama.cpp/archive/3cf03257f219afbe7334045ff7c6a06ac68c627d.zip
unzip 3cf03257f219afbe7334045ff7c6a06ac68c627d.zip
mkdir -p third_party && mv llama.cpp-3cf03257f219afbe7334045ff7c6a06ac68c627d third_party/llama.cpp

# 4. 构建(纯离线:llama.cpp 来自上下文,apt/pip 走清华源;实测 2m45s @16 核)
docker compose build

# 5. 配置 + 启动
cp .env.example .env          # 按需改 MODEL / CONTEXT / API_KEY / HOST_PORT
docker compose up -d          # healthy 约 1 分钟(卷上已有模型时)
```

首次启动会下载模型(走 ModelScope,IQ3_S 83.6 GB 实测约 35 分钟 @43 MB/s,
SHA-256 逐文件校验)。同代 CPU 的机器也可以跳过 2-4:`docker load` 备份的
镜像(引擎按构建机 CPU 原生编译,跨代 CPU 需走构建)。

## 已验证的基准(官方方法:bench/results/2026-09-30-community-rtx-5090/benchmark.py,
全新 prompt ×3 轮中位、256 token 输出、贪心;逐轮 JSON 在数据卷 /data/bench/)

上下文 131072 / 262144(256K 为模型原生窗口),prefill 与 decode tok/s:

| 档位 | 4K | 32K | 128K | 256K |
| --- | --- | --- | --- | --- |
| IQ3_S | 5186/5159 · 193/191 | 6645/6660 · 207/193 | 6353/6366 · 189/187 | - / 5948 · - / 202 |
| UD-IQ4_XS | 2529/2506 · 130/137 | 3708/3635 · 153/142 | 3622/3613 · 160/174 | - / 3412 · - / 145 |
| UD-Q4_K_XL | 2009/1993 · 90/88 | 2948/3086 · 90/89 | 2927/3010 · 92/92 | - / 2643 · - / 88 |

每格为 ctx131072/ctx262144 两次测量的 prefill · decode。IQ3_S 专家全显存命中
(hit_rate 0.99); UD 档走 RAM 预算(55/71 GiB)。

## 升级到官方新版本(封盘策略,不做 rebase)

1. `git fetch upstream --tags`(upstream = Niko1221/Strata)。
2. `git checkout -b deploy/v0.1.42-cn v0.1.42` —— 从官方 release tag 开全新分支
   (只认 tag,不从 main 切)。
3. 复制部署文件(零冲突):
   `git checkout deploy/v0.1.41-cn -- docker-compose.yml .env.example`
4. 手工套用两处改动并对照新版文件复核:
   - Dockerfile:FROM 换阿里云镜像 + apt sed + PIP_INDEX_URL ENV;
   - .dockerignore:注释掉 `third_party/llama.cpp/` 一行(保留注释块)。
5. `git tag -a v0.1.42-cn.1`,重建镜像 `strata:v0.1.42-cn.1`,compose/.env 里
   换 image 名,`docker compose up -d`。旧分支/tag/镜像永久保留作回滚。

## 已踩过的坑

- 构建沙箱的网络与宿主机不一致:宿主机可达 github 不代表构建内可达;
  .dockerignore 的上游设计会在构建内从 github 下载 llama.cpp——本分支已改为
  使用预置树,不要恢复那行排除。
- 清构建缓存(`docker builder prune`)会连带清掉 `docker/dockerfile:1` 前端,
  下次构建会卡死在解析 Dockerfile;重建前先 `docker pull docker/dockerfile:1`。
- 数据卷 `strata-data` 约 286 GB(三档模型),宿主机 /home 分区注意余量。
