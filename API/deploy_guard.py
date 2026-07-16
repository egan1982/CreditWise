"""
轻量部署审批开关 —— 替代完整机器指纹绑定的默认方案

不做强绑定，只做"部署需要经过你知情"的软控制。
适用于：内部多服务器/PC 部署，防止源码被随意复制运行，而非防范外部商业窃取。

集成方式：在 API/main.py 的 create_app() 最前面调用 check_deploy_approved()。

设计决策（见 docs/code-protection-plan.md §3.0）：
- 本项目当前场景（内部多服务器/PC 部署）不需要机器指纹绑定，
  Cython 编译 + Docker 镜像已解决"无源码可看"，控制分发渠道本身即是主要防线
- 若未来需要交付给不受控的外部客户，可平滑升级为 API/license_validator.py
  的 Ed25519 签名 + 机器指纹绑定完整方案

用法：
    部署方在 .env 或 docker-compose 环境变量中配置:
        DEPLOY_APPROVAL_TOKEN_EXPECTED=<本次部署约定的 token>
        DEPLOY_APPROVAL_TOKEN=<与预期值匹配的 token>

    两者不匹配则应用拒绝启动，抛出 RuntimeError。
    DEPLOY_APPROVAL_TOKEN_EXPECTED 未配置 → 视为不启用审批门槛（开发环境兼容）。
"""

import os


def check_deploy_approved() -> bool:
    """
    启动时校验部署审批标记。

    Returns:
        True:  审批通过（或未启用审批门槛，开发/兼容模式）
        False: 审批未通过，应拒绝启动
    """
    expected = os.environ.get("DEPLOY_APPROVAL_TOKEN_EXPECTED", "")
    actual = os.environ.get("DEPLOY_APPROVAL_TOKEN", "")

    if not expected:
        # 未配置期望值 → 视为不启用审批门槛（开发环境/向后兼容）
        return True

    if actual == expected:
        return True

    print(
        "[DEPLOY_GUARD] 部署审批未通过: "
        "DEPLOY_APPROVAL_TOKEN 与预期值不匹配，拒绝启动"
    )
    return False
