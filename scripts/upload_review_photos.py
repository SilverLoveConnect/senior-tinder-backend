"""심사용 데모 프로필 사진을 S3에 올리고 URL 목록을 남긴다.

`seed_review.py`가 읽을 `review_photos.json`을 만든다.

키 규칙
-------
    photos/review-demo/{index}.{jpg|png}

`/review-demo/` 마커가 롤백의 식별자다. 실제 가입자 사진은
`photos/{user_id}/{uuid}.ext`(users.py 참조)이라 절대 겹치지 않는다.

자격증명
--------
AWS 키는 Railway 환경변수에 있다. `railway run`으로 실행하면 값이 프로세스에
주입되므로 키를 화면에 띄우거나 파일에 적을 필요가 없다.

    railway run python scripts/upload_review_photos.py            # dry-run
    railway run python scripts/upload_review_photos.py --apply    # 업로드
    railway run python scripts/upload_review_photos.py --delete --apply  # 되돌리기

업로드 후 각 URL에 HEAD 요청을 보내 공개 접근이 되는지 확인한다.
버킷이 비공개면 앱에서 사진이 안 뜨므로 여기서 미리 걸러야 한다.
"""

import argparse
import json
import mimetypes
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv()

import boto3  # noqa: E402

from app.core.config import settings  # noqa: E402

ASSET_DIR = Path("/Users/hanjisoo/Downloads/어플 개발 기획/review_assets")
MANIFEST_OUT = Path(__file__).resolve().parent / "review_photos.json"
KEY_PREFIX = "photos/review-demo/"


def s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def public_url(key: str) -> str:
    # users.py의 업로드 경로와 동일한 형식이어야 한다.
    return (f"https://{settings.AWS_S3_BUCKET}.s3."
            f"{settings.AWS_REGION}.amazonaws.com/{key}")


def check_env() -> bool:
    missing = [n for n in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_BUCKET")
               if not getattr(settings, n, "")]
    if missing:
        print("❌ 환경변수 누락:", ", ".join(missing))
        print("   `railway run python scripts/upload_review_photos.py ...` 로 실행하세요.")
        return False
    return True


def local_files() -> list[Path]:
    """업로드할 이미지. 같은 이름의 .jpg가 있으면 그쪽을 쓴다.

    생성 원본은 1024px PNG로 장당 ~1.5MB인데, 프로필 카드 한 장에 그만한
    용량을 쓰면 느린 회선에서 카드가 늦게 뜬다(50대 타겟에겐 특히 체감된다).
    같은 폴더에 1080px JPEG(q86)를 만들어 두면 장당 ~136KB로 떨어진다.
    PNG는 마스터로 남겨둔다.
    """
    if not ASSET_DIR.exists():
        print(f"❌ 이미지 폴더가 없습니다: {ASSET_DIR}")
        return []
    by_stem: dict[str, Path] = {}
    for p in sorted(ASSET_DIR.glob("*.png")) + sorted(ASSET_DIR.glob("*.jpg")):
        if p.name.startswith("_"):
            continue
        # jpg가 뒤에 오므로 같은 stem이면 자연히 jpg가 이긴다
        by_stem[p.stem] = p
    return [by_stem[k] for k in sorted(by_stem)]


def head_ok(url: str) -> str:
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return f"{r.status}"
    except Exception as e:
        code = getattr(e, "code", None)
        return f"실패({code or type(e).__name__})"


def do_upload(apply: bool) -> int:
    files = local_files()
    if not files:
        return 1

    print(f"업로드 대상 {len(files)}장 → s3://{settings.AWS_S3_BUCKET}/{KEY_PREFIX}\n")
    urls: dict[str, str] = {}
    client = s3_client() if apply else None

    for path in files:
        index = path.stem                      # "0001"
        key = f"{KEY_PREFIX}{index}{path.suffix}"
        url = public_url(key)
        urls[index] = url
        size_kb = path.stat().st_size // 1024
        if apply:
            ctype = mimetypes.guess_type(path.name)[0] or "image/png"
            with open(path, "rb") as f:
                client.upload_fileobj(f, settings.AWS_S3_BUCKET, key,
                                      ExtraArgs={"ContentType": ctype})
            print(f"  ↑ {path.name} ({size_kb}KB)  공개확인={head_ok(url)}")
        else:
            print(f"  · {path.name} ({size_kb}KB) → {key}")

    if not apply:
        print("\n🔎 dry-run — 아무것도 올리지 않았습니다. 실제 업로드는 --apply")
        return 0

    with open(MANIFEST_OUT, "w") as f:
        json.dump(urls, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 업로드 완료 — URL 목록: {MANIFEST_OUT}")
    print("   다음: railway run python scripts/seed_review.py --apply")
    return 0


def do_delete(apply: bool) -> int:
    client = s3_client()
    resp = client.list_objects_v2(Bucket=settings.AWS_S3_BUCKET, Prefix=KEY_PREFIX)
    keys = [o["Key"] for o in resp.get("Contents", [])]
    print(f"삭제 대상 {len(keys)}개 (s3://{settings.AWS_S3_BUCKET}/{KEY_PREFIX})")
    for k in keys:
        print("  -", k)
    if not keys:
        return 0
    if not apply:
        print("\n🔎 dry-run — 아무것도 지우지 않았습니다. 실제 삭제는 --delete --apply")
        return 0
    client.delete_objects(Bucket=settings.AWS_S3_BUCKET,
                          Delete={"Objects": [{"Key": k} for k in keys]})
    if MANIFEST_OUT.exists():
        MANIFEST_OUT.unlink()
    print("\n✅ S3 삭제 완료 (review_photos.json도 제거)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="심사용 데모 사진 S3 업로드/삭제")
    p.add_argument("--apply", action="store_true", help="실제로 수행. 없으면 dry-run.")
    p.add_argument("--delete", action="store_true", help="업로드 대신 삭제(롤백).")
    args = p.parse_args()

    if not check_env():
        return 1
    return do_delete(args.apply) if args.delete else do_upload(args.apply)


if __name__ == "__main__":
    sys.exit(main())
