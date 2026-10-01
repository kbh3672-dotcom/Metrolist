#!/usr/bin/env python3
"""
추가 패치: 가로모드에서 우측 하단 '가사' 버튼을 누르면
  공유 버튼  -> 전체화면 버튼
  ... 버튼   -> 가사 메뉴(수정 등) 버튼
으로 전환되게 합니다. (다른 부분은 건드리지 않음)

먼저 patch_player.py가 적용된 Player.kt에서만 동작합니다.
사용법: python patch_lyrics_toggle.py [Player.kt 경로]
"""
import os
import re
import sys

MARK = "// [custom-landscape]"
MARK2 = "// [custom-lyrics-toggle]"


def find_player():
    if len(sys.argv) > 1:
        return sys.argv[1]
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", "build", ".gradle")]
        if "Player.kt" in files:
            p = os.path.join(root, "Player.kt")
            with open(p, encoding="utf-8") as f:
                if "fun BottomSheetPlayer(" in f.read():
                    return p
    sys.exit("Player.kt를 찾지 못했어요. 경로를 인자로 넣어주세요.")


NEW_BUTTONS = """AnimatedContent(
                            targetState = showInlineLyrics,
                            label = "LandscapeButtons",
                        ) { showLyrics ->
                            MARK2_PLACEHOLDER
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                if (showLyrics) {
                                    // 가사 모드: 전체화면 버튼 + 가사 메뉴(...) 버튼
                                    Box(
                                        modifier =
                                            Modifier
                                                .size(40.dp)
                                                .clip(RoundedCornerShape(24.dp))
                                                .background(textButtonColor)
                                                .clickable { isFullScreen = !isFullScreen },
                                    ) {
                                        Icon(
                                            painter = painterResource(R.drawable.fullscreen),
                                            contentDescription = null,
                                            tint = iconButtonColor,
                                            modifier =
                                                Modifier
                                                    .align(Alignment.Center)
                                                    .size(24.dp),
                                        )
                                    }

                                    Spacer(modifier = Modifier.width(12.dp))

                                    val currentLyrics by playerConnection.currentLyrics.collectAsStateWithLifecycle(initialValue = null)
                                    Box(
                                        modifier =
                                            Modifier
                                                .size(40.dp)
                                                .clip(RoundedCornerShape(24.dp))
                                                .background(textButtonColor)
                                                .clickable {
                                                    menuState.show {
                                                        com.metrolist.music.ui.menu.LyricsMenu(
                                                            lyricsProvider = { currentLyrics },
                                                            songProvider = { currentSong?.song },
                                                            mediaMetadataProvider = { mediaMetadata },
                                                            onDismiss = menuState::dismiss,
                                                            onShowOffsetDialog = {
                                                                bottomSheetPageState.show {
                                                                    ShowOffsetDialog(
                                                                        songProvider = { currentSong?.song },
                                                                    )
                                                                }
                                                            },
                                                        )
                                                    }
                                                },
                                    ) {
                                        Icon(
                                            painter = painterResource(R.drawable.more_horiz),
                                            contentDescription = null,
                                            tint = iconButtonColor,
                                            modifier =
                                                Modifier
                                                    .align(Alignment.Center)
                                                    .size(24.dp),
                                        )
                                    }
                                } else {
                                    // 기본 모드: 공유 버튼 + 더보기 버튼
                                    Box(
                                        modifier =
                                            Modifier
                                                .size(40.dp)
                                                .clip(RoundedCornerShape(24.dp))
                                                .background(textButtonColor)
                                                .clickable {
                                                    val intent =
                                                        Intent().apply {
                                                            action = Intent.ACTION_SEND
                                                            type = "text/plain"
                                                            putExtra(
                                                                Intent.EXTRA_TEXT,
                                                                "https://music.youtube.com/watch?v=${mediaMetadata.id}",
                                                            )
                                                        }
                                                    context.startActivity(Intent.createChooser(intent, null))
                                                },
                                    ) {
                                        Icon(
                                            painter = painterResource(R.drawable.share),
                                            contentDescription = null,
                                            tint = iconButtonColor,
                                            modifier =
                                                Modifier
                                                    .align(Alignment.Center)
                                                    .size(24.dp),
                                        )
                                    }

                                    Spacer(modifier = Modifier.width(12.dp))

                                    PlayerMoreMenuButton(
                                        mediaMetadata = mediaMetadata,
                                        state = state,
                                        textButtonColor = textButtonColor,
                                        iconButtonColor = iconButtonColor,
                                    )
                                }
                            }
                        }""".replace("MARK2_PLACEHOLDER", MARK2)


def main():
    path = find_player()
    with open(path, encoding="utf-8", newline="") as f:
        src = f.read().replace("\r\n", "\n")

    if MARK not in src:
        sys.exit("먼저 patch_player.py를 적용해야 해요. ([custom-landscape] 표시가 없음)")
    if MARK2 in src:
        sys.exit("이미 패치된 파일이에요. (중복 적용 방지)")

    base = src.index(MARK)

    # 공유 버튼 Box 시작 위치 (가로모드 헤더 안의 첫 번째 것)
    start_pat = re.compile(
        r'Box\(\s*modifier =\s*Modifier\s*\.size\(40\.dp\)\s*'
        r'\.clip\(RoundedCornerShape\(24\.dp\)\)\s*'
        r'\.background\(textButtonColor\)\s*'
        r'\.clickable \{\s*val intent ='
    )
    ms = start_pat.search(src, base)
    if not ms:
        sys.exit("[실패] 공유 버튼 위치를 못 찾았어요.")

    # 더보기 버튼 호출 끝 위치
    end_pat = re.compile(
        r'PlayerMoreMenuButton\(\s*mediaMetadata = mediaMetadata,\s*'
        r'state = state,\s*textButtonColor = textButtonColor,\s*'
        r'iconButtonColor = iconButtonColor,\s*\)'
    )
    me = end_pat.search(src, ms.end())
    if not me:
        sys.exit("[실패] 더보기 버튼 위치를 못 찾았어요.")

    src = src[: ms.start()] + NEW_BUTTONS + src[me.end():]

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    print(f"패치 완료: {path}")


if __name__ == "__main__":
    main()
