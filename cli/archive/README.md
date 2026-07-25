# Blogdex 아카이브 스크립트

이 디렉토리는 **일회성 실행** 또는 **실험적 기능**으로
더 이상 사용되지 않는 Python 스크립트를 보관합니다.

## 보관 사유

| 파일 | 사유 | 대체/비고 |
|------|------|-----------|
| `spam_cleanup.py` | 일회성 스팸 정리 작업 | 작업 완료 후 불필요 |
| `spam_cleanup2.py` | spam_cleanup.py의 변형 | 중복, 작업 완료 |
| `spam_inspect.py` | 스팸 URL 인스펙션 | 일회성 작업 |
| `ga4_inject.py` | Hugo 사이트 GA4 측정ID 삽입 | 이미 삽입 완료 |
| `ga4_inject2.py` | ga4_inject.py 변형 | 중복 |
| `ga4_audit.py` | GA4 속성 감사 | 감사 완료 |
| `ga4_cleanup.py` | GA4 속성 정리 | 정리 완료 |
| `ga4_measurement_ids.py` | GA4 측정ID 조회 | 일회성 조회 |
| `index_submit.py` | Google Indexing API 제출 | `daily_sync.py`에서 간헐적 호출 → 제거 검토 |
| `gsc_backfill_pages.py` | GSC 페이지별 백필 | 실험적, 미완료 |

## 복원 방법

```bash
git mv cli/archive/<filename>.py cli/<filename>.py
```

또는 직접 복사:

```bash
cp cli/archive/<filename>.py cli/<filename>.py
```

> 참고: 이 파일들은 삭제되지 않았습니다. 필요시 언제든 복원 가능합니다.
