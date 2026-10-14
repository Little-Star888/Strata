# DEPLOY-CN.md — deploy/v0.1.44.1-cn(原版单一栈,NVFP4 收编版)

单栈回到原版仓库:上游 0.1.44 把 sergqwer/strata-nvfp4 的 NVFP4 引擎路径移植进了
主线(sergiywith 移植,MIT),setup 原生支持 NVFP4。本分支 = 官方 v0.1.44.1 tag +
三处 cn 补丁 + 两个 cn 部署文件,没有改任何引擎源码。

## 与 fork 部署(deploy/v0.1.42-nvfp4.2-cn)的关系

- 模型文件 100% 复用:GPTQ pack 与上游 pin 的 SHA-256 逐字节一致(index.txt 已核对),
  IQ3_S / UD 两档本就是上游体系;`models/` 整体 `mv` 过来,零拷贝。
- 已配档位(IQ3_S / UD-IQ4_XS / UD-Q4_K_XL / NVFP4 / NVFP4-MIX / NVFP4-Q8)的配置
  JSON 随 `models/` 一起移来,入口脚本原样复用——上下文 524288、vision、密钥、
  去审查控制向量都已烧在里面,首次启动无需 setup。
- fork 独有、本分支的处理:
  - uncensored:上游 setup 无 `--uncensored`;`cn-apply-uncensor.py` 把与 fork 完全
    相同的引擎参数写进新生成的配置。向量文件随本分支走
    (`data/uncensor/` → 镜像内 `/opt/strata/data/uncensor/`,与 fork 路径一致)。
  - NVFP4-MIX / NVFP4-Q8:上游 setup 无此二条目。已有配置则照常复用;配置缺失时
    入口明确报错退出(引擎能否加载未验证,验证前 fork 栈是这两包的备用)。
- 回滚:`models/` `mv` 回 fork 目录 + fork `docker compose up -d`,原样恢复。

## 与 0.1.43-cn 的差异(升级收益)

- 引擎 0.1.42 → 0.1.44.1:0.1.43.1 的桌面卡 adaptive-overlap 修复、长提示 mmap
  看门狗修复;0.1.44 的 NVFP4 收编、#2228 图片哈希缓存(带图长对话不再整段重读)、
  strata_kq K 量化 prompt 内核(opt-in)、批槽 503、`</tool_call>` 等服务器修复。
- 新档位:UD-Q5_K_XL(108G RAM)/ UD-Q6_K_XL(118G)/ Q8_0(136G,超本机内存)、
  NVFP4-NVIDIA、Qwen3.6-35B-A3B 家族。
- MIN_ENGINE=(0,1,44,1)。IQ3_S 成为上游推荐默认档(0.1.44 起);不影响已配档位。

## 复活 / 切换步骤

1. `docker compose build`(本地有阿里云基础镜像缓存 + 预置 llama.cpp 3cf0325,离线可建;
   清过构建缓存先 `docker pull docker/dockerfile:1`);
2. `cp .env.example .env`,按需改 MODEL/API_KEY;
3. 首次启动会对已有模型文件做一次完整性校验(experts.bin 68GB 哈希需几分钟,一次性);
4. 切换顺序:停 fork 容器 → `mv` models → 本目录 `docker compose up -d`。

## 基准方法(官方)

全新提示 ×3 轮中位、256 token 输出、贪心;prefill = 新读 token ÷ prompt_ms,
decode = 生成 token ÷ decode_ms,数字取自 `/metrics`。逐档 JSON 在 `models/bench/`。
本机历史对照(RTX 5090 / 9950X / DDR5-3600,262K 档,256K 点):IQ3_S 189/5906,
UD-Q4_K_XL 88/2845(0.1.43 引擎),GPTQ 140/5943,mix 69/6687,q8 42/2805
(prefill/decode tok/s)。升级后先跑三主力(IQ3_S / UD-Q4_K_XL / NVFP4-GPTQ)对照,
回退阈值:decode 掉幅超过 10% 且无法用环境变量解释。

## 已踩的坑(历史沿用)

- 改 `/data/config/*.json` 必须先 `docker stop`(停止时写回会覆盖外部修改);
- 改已配档位的设置(CONTEXT/VISION/API_KEY/UNCENSORED)流程:.env 改值 + 临时
  `REINSTALL=1` + `docker compose up -d`,起来后删 REINSTALL;
- 清构建缓存会连带删 `docker/dockerfile:1` 前端,重建前先 pull;
- 密钥永不入库:`/.env` 已 gitignore,模板一律占位符(2026-10-11 事故教训)。
