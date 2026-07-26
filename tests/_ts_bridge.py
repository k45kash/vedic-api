"""Мостик к калькуляторам на TypeScript.

Часть расчётного ядра живёт не в Python, а во фронтенде: Раху/Гулика/Ямаганда
(`frontend-nuxt/utils/kalam.ts`), ашта-кута (`calculators/kuta.ts`), подбор
события (`calculators/event-picker.ts`). Два из трёх тихих дефектов, ради
которых заводились эти тесты, — именно там, поэтому проверять их надо
исполнением настоящего кода, а не пересказом его логики на Python.

Node с версии 22 умеет исполнять .ts напрямую (стирание типов), так что
сборка не нужна. Два расхождения с резолвером Nuxt закрываются хуком:

  * `import X from '../content/x.json'` — Nuxt разрешает, node требует
    `with { type: 'json' }`;
  * `import { taraFor } from './tara'` — Nuxt дописывает расширение, node нет.

Если node недоступен, тесты, использующие мостик, пропускаются: расчётное
ядро на Python от них не зависит.
"""

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend-nuxt"

# Хук резолвера: JSON без import-атрибутов и импорты без расширения.
_HOOK = """\
import { registerHooks } from 'node:module'
registerHooks({
  resolve(spec, ctx, next) {
    if (spec.endsWith('.json')) {
      ctx = { ...ctx, importAttributes: { ...(ctx.importAttributes || {}), type: 'json' } }
    }
    let r
    try { r = next(spec, ctx) }
    catch (e) {
      if (e.code !== 'ERR_MODULE_NOT_FOUND' || !spec.startsWith('.')) throw e
      r = next(spec + '.ts', ctx)
    }
    if (r.url.endsWith('.json')) { r.format = 'json'; r.importAttributes = { type: 'json' } }
    return r
  },
})
"""


def _node():
    exe = shutil.which("node")
    if not exe:
        pytest.skip("node не установлен — TypeScript-калькуляторы не проверяем")
    return exe


def run_ts(script: str, tmp_path: Path):
    """Исполняет ES-модуль в node, возвращает напечатанный им JSON.

    Скрипту доступны:
      * `FE` — file-URL каталога `frontend-nuxt/` со слэшем на конце, чтобы
        писать `await import(FE + 'utils/kalam.ts')`;
      * `out(значение)` — печать результата (последний вызов и возвращается).
    """
    exe = _node()
    hook = tmp_path / "hook.mjs"
    hook.write_text(_HOOK, encoding="utf-8")
    src = tmp_path / "run.mjs"
    src.write_text(
        f"const FE = {json.dumps(FRONTEND.as_uri() + '/')}\n"
        "const out = (v) => console.log('@@' + JSON.stringify(v))\n"
        + textwrap.dedent(script),
        encoding="utf-8",
    )

    p = subprocess.run(
        [exe, "--import", hook.as_uri(), src.as_posix()],
        cwd=FRONTEND, capture_output=True, text=True, timeout=60,
    )
    if p.returncode != 0:
        pytest.fail(f"node упал:\n{p.stderr[-2000:]}")
    строки = [s for s in p.stdout.splitlines() if s.startswith("@@")]
    assert строки, f"скрипт ничего не вернул. stdout={p.stdout!r} stderr={p.stderr[-500:]!r}"
    return json.loads(строки[-1][2:])
