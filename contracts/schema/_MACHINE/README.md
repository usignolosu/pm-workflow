# contracts/schema/_MACHINE/

> v4.0.1：此目录命名原因说明
>
> `_MACHINE/` 是 `contracts/schema/` 下专供"机器读取、不直接面向 PM"的子目录。
> 与平铺的 `*.yaml` 不同——这里放的 YAML 是**校验器和脚本专属配置**：
>
> - `versioning.yaml` — SemVer 版本管理
> - `scale_routing.yaml` — Scale-aware 路由表
> - `validation_rules.yaml` — 校验器规则
>
> PM 看 `contracts/README.md` 即可，不需要进 `_MACHINE/`。
> 
> v4.0.1 决策：**不重命名**（`_MACHINE` 比 `_internal`/`_impl` 表达力更好，且 `query_kg.py` 已硬引用此路径）。