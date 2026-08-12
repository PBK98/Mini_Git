# Mini Git Manual

이 문서는 `mini_git` 프로그램을 직접 실행하고 테스트하기 위한 사용법입니다.

## 실행 방법

모듈 실행 방식으로 실행합니다.

```bash
python3 -m mini_git
```

환경에서 `python` 명령이 Python 3에 연결되어 있다면 다음 방식도 사용할 수 있습니다.

```bash
python -m mini_git
```

실행하면 REPL 프롬프트가 표시됩니다.

```text
Mini Git REPL. Type 'help' for commands.
mini-git>
```

현재 구현은 메모리 기반입니다. 프로그램을 종료하면 저장소, 브랜치, 커밋 히스토리는 저장되지 않습니다.

## 명령어 규칙

명령어는 대소문자를 구분하지 않습니다.

```text
INIT Alice
init Alice
```

문자열 인자는 공백을 포함할 수 있습니다. 공백이 있으면 따옴표로 감쌉니다.

```text
COMMIT "Add login feature"
SEARCH "login"
```

## 필수 명령어

### INIT

처음 실행하면 저장소를 초기화하고 `main` 브랜치와 현재 작성자를 설정합니다.

이미 초기화된 상태에서 다른 사용자명으로 다시 실행하면 기존 커밋, 브랜치, HEAD와 검색 인덱스는 유지되고 현재 작성자만 변경됩니다.

```text
INIT <user_name>
```

예시:

```text
init "Alice"
```

출력 예시:

```text
Initialized repository.
Current branch: main
Current user: Alice
```

작성자 변경 예시:

```text
mini-git> init Bob
Repository already initialized.
Current branch: main
Current user: Bob
```

이후 생성한 커밋의 작성자는 `Bob`으로 기록되며, `LOG --sort-by=date`와 `LOG --sort-by=author`에는 이전 작성자의 커밋도 함께 출력됩니다.

기존 커밋과 브랜치, 그래프, 검색 인덱스를 삭제하고 새 저장소 상태로 돌아가려면 `--reset` 옵션을 사용합니다.

```text
mini-git> init --reset Carol
Reinitialized repository.
Current branch: main
Current user: Carol
```

초기화 후에는 `main` 브랜치만 존재하고 커밋 로그는 비어 있습니다. 세션 내 커밋 해시 중복을 막기 위한 내부 카운터와 발급 해시 기록은 유지됩니다.

### WHOIAM

현재 커밋 작성자로 설정된 사용자를 확인합니다.

```text
WHOIAM
```

출력 예시:

```text
Current user: Bob
```

### BRANCH

인자 없이 실행하면 생성된 브랜치 목록을 출력합니다. 현재 브랜치 앞에는 `*`가 표시됩니다.

```text
BRANCH
```

출력 예시:

```text
Branches:
* main
  feature
```

브랜치 이름을 입력하면 현재 HEAD를 가리키는 새 브랜치를 생성합니다.

현재 HEAD가 있어야 하므로 첫 커밋을 만든 후 사용할 수 있습니다.

```text
BRANCH <branch_name>
```

예시:

```text
branch feature
```

### SWITCH

현재 브랜치를 지정한 브랜치로 변경합니다.

```text
SWITCH <branch_name>
```

예시:

```text
switch feature
```

### COMMIT

현재 HEAD를 부모로 하는 새 커밋을 생성합니다. 커밋에는 `hash`, `message`, `author`, `timestamp`, `parents`가 저장됩니다.

```text
COMMIT <message>
```

예시:

```text
commit "Initial commit"
```

출력 예시:

```text
[main a1b2c3] Initial commit
```

### LOG

커밋 목록을 출력합니다. 기본 LOG는 부모 커밋이 자식 커밋보다 먼저 출력되는 위상 정렬 순서를 따릅니다.

```text
LOG
```

정렬 옵션도 사용할 수 있습니다.

```text
LOG --sort-by=date
LOG --sort-by=author
```

### PATH

두 커밋 사이의 최단 경로를 출력합니다. 커밋-부모 연결을 무방향 간선으로 보고 탐색합니다.

```text
PATH <commit1> <commit2>
```

전체 해시 대신 유일한 해시 prefix도 사용할 수 있습니다.

```text
path a1b2c3 g7h8i9
```

경로가 없으면 다음을 출력합니다.

```text
No path
```

### ANCESTORS

지정한 커밋에서 도달 가능한 모든 조상 커밋을 출력합니다.

```text
ANCESTORS <commit_hash>
```

예시:

```text
ancestors d4e5f6
```

### SEARCH

커밋 메시지 키워드로 커밋을 검색합니다. 메시지는 공백 기준으로 분리하고 소문자로 정규화해 인덱싱합니다.

```text
SEARCH <keyword>
```

예시:

```text
search login
search "login feature"
```

공백 검색어는 각 단어의 역색인으로 후보를 좁힌 뒤 해당 구문이 포함된 메시지를 찾습니다.

작성자 기준 검색도 지원합니다.

```text
SEARCH --author=<name>
```

`name`에는 브랜치명이 아니라 `INIT`에서 설정한 사용자명을 입력합니다. 옵션 이름은 `--author`입니다.

예시:

```text
search --author=Alice
```

### exit / quit

REPL을 정상 종료합니다.

```text
exit
```

## 빠른 테스트 시나리오

아래 순서대로 입력해볼 수 있습니다.

```text
init "Alice"
commit "Initial commit"
branch feature
switch feature
commit "Add login feature"
switch main
commit "Add payment feature"
log
search login
log --sort-by=author
exit
```

예상 흐름:

```text
mini-git> init "Alice"
Initialized repository.
Current branch: main
Current user: Alice
mini-git> commit "Initial commit"
[main <hash>] Initial commit
mini-git> branch feature
Created branch: feature
mini-git> switch feature
Switched to branch: feature
```

## 종료 코드 확인

직전 명령의 종료 코드는 `$?`로 확인합니다.

```bash
python3 -m mini_git
echo $?
```

현재 종료 코드 기준:

```text
0   정상 종료
1   일반 오류, 런타임 오류, EOF 종료, OSError, 예상 밖 예외
2   명령 파싱 오류, 잘못된 명령 사용법, 알 수 없는 명령
130 Ctrl-C 종료
```

`Ctrl-C`와 EOF는 REPL 종료 흐름으로 처리하고, `OSError` 같은 입출력 환경 문제는 `EnvError` 경로에서 처리합니다.

예시:

```bash
printf 'exit\n' | python3 -m mini_git
echo $?
# 0
```

```bash
printf 'commit\nexit\n' | python3 -m mini_git
echo $?
# 2
```

REPL 실행 중 `Ctrl-C`를 누르면 종료 코드는 `130`입니다.

## 에러 예시

INIT 전 커밋:

```text
mini-git> commit first
app error: repository is not initialized
```

잘못된 명령어:

```text
mini-git> unknown
app error: unknown command: unknown
```

없는 브랜치 전환:

```text
mini-git> switch missing
app error: unknown branch: missing
```
