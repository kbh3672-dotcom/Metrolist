#!/usr/bin/env python3
"""
Metrolist 가로모드 커스텀 패치 (구형 플레이어 기준)

사용법 (repo 루트에서):
    python patch_player.py                 # Player.kt 자동 탐색
    python patch_player.py 경로/Player.kt   # 경로 직접 지정

적용 내용 (가로모드에서만 동작, 세로모드는 그대로):
 1. 화면 좌측 절반: 가사 항상 고정
 2. 화면 우측 절반: 플레이어 항상 고정
 3. 우측 하단: 제목/아티스트 ~ 슬라이더 ~ 재생 컨트롤
 4. 우측 상단: 슬라이더 폭에 맞춘 정사각형 큰 썸네일 (모서리 24dp = 재생 중 일시정지 버튼 곡률)
 5. 제목: 슬라이더와 같은 폭, 길면 계속 반복해서 흐름
 6. 제목/아티스트 옆 작은 썸네일 제거
 7. 공유/더보기 버튼은 제목 아랫줄(아티스트 줄) 오른쪽으로 이동
"""
import os
import re
import sys

MARK = "// [custom-landscape]"


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


# ---------------------------------------------------------------
# (A) controlsContent 맨 위쪽: 제목/아티스트/공유/더보기 가로모드 전용 헤더
# ---------------------------------------------------------------
HEADER_LANDSCAPE = """if (isLandscape) {
                MARK_PLACEHOLDER
                Column(
                    modifier =
                        Modifier
                            .fillMaxWidth()
                            .padding(horizontal = PlayerHorizontalPadding),
                ) {
                    AnimatedContent(
                        targetState = mediaMetadata.title,
                        transitionSpec = { fadeIn() togetherWith fadeOut() },
                        modifier = Modifier.fillMaxWidth(),
                        label = "",
                    ) { title ->
                        Text(
                            text = title,
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            color = TextBackgroundColor,
                            modifier =
                                Modifier
                                    .basicMarquee(
                                        iterations = Int.MAX_VALUE,
                                        initialDelayMillis = 1000,
                                        velocity = 30.dp,
                                    ).combinedClickable(
                                        enabled = true,
                                        indication = null,
                                        interactionSource = remember { MutableInteractionSource() },
                                        onClick = {
                                            val albumId = mediaMetadata.album?.id
                                                ?: currentSong?.album?.id
                                                ?: currentSong?.song?.albumId
                                            if (albumId != null) {
                                                navController.navigate("album/$albumId")
                                                state.collapseSoft()
                                            }
                                        },
                                        onLongClick = {
                                            val clip = ClipData.newPlainText(copiedTitleStr, title)
                                            clipboardManager.setPrimaryClip(clip)
                                            Toast.makeText(context, copiedTitleStr, Toast.LENGTH_SHORT).show()
                                        },
                                    ),
                        )
                    }

                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        if (mediaMetadata.explicit) MIcon.Explicit()

                        val artistText =
                            mediaMetadata.artists
                                .map { it.name }
                                .filter { it.isNotBlank() }
                                .joinToString(", ")

                        Text(
                            text = artistText,
                            style = MaterialTheme.typography.titleMedium,
                            color = TextBackgroundColor,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier =
                                Modifier
                                    .weight(1f)
                                    .basicMarquee(iterations = 1, initialDelayMillis = 3000, velocity = 30.dp)
                                    .combinedClickable(
                                        enabled = true,
                                        indication = null,
                                        interactionSource = remember { MutableInteractionSource() },
                                        onClick = {
                                            val artistId =
                                                mediaMetadata.artists
                                                    .firstOrNull { !it.id.isNullOrBlank() }
                                                    ?.id
                                            if (artistId != null) {
                                                navController.navigate("artist/$artistId")
                                                state.collapseSoft()
                                            }
                                        },
                                        onLongClick = {
                                            val clip = ClipData.newPlainText(copiedArtistStr, artistText)
                                            clipboardManager.setPrimaryClip(clip)
                                            Toast.makeText(context, copiedArtistStr, Toast.LENGTH_SHORT).show()
                                        },
                                    ),
                        )

                        Spacer(modifier = Modifier.width(12.dp))

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
            }""".replace("MARK_PLACEHOLDER", MARK)


# ---------------------------------------------------------------
# (B) 가로모드 전체 레이아웃: 좌 가사 / 우 (큰 썸네일 + 하단 플레이어)
# ---------------------------------------------------------------
LANDSCAPE_BODY = """Row(
                    modifier =
                        Modifier
                            .windowInsetsPadding(
                                WindowInsets.systemBars.only(WindowInsetsSides.Horizontal).add(verticalWindowInsets),
                            ).padding(bottom = 24.dp)
                            .fillMaxSize(),
                ) {
                    // 좌측 절반: 가사 항상 고정
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier =
                            Modifier
                                .weight(1f)
                                .fillMaxSize()
                                .nestedScroll(state.preUpPostDownNestedScrollConnection),
                    ) {
                        InlineLyricsView(
                            mediaMetadata = mediaMetadata,
                            showLyrics = true,
                            positionProvider = { effectivePosition },
                        )
                    }

                    // 우측 절반: 위 = 큰 썸네일, 아래 = 플레이어
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier =
                            Modifier
                                .weight(1f)
                                .fillMaxSize()
                                .windowInsetsPadding(WindowInsets.systemBars.only(WindowInsetsSides.Top))
                                .padding(bottom = QueuePeekHeight),
                    ) {
                        BoxWithConstraints(
                            contentAlignment = Alignment.TopCenter,
                            modifier =
                                Modifier
                                    .weight(1f)
                                    .fillMaxWidth()
                                    .padding(top = 8.dp, bottom = 16.dp),
                        ) {
                            // 슬라이더와 같은 폭의 정사각형 (세로 공간이 모자라면 그에 맞춤)
                            val coverSize =
                                maxOf(
                                    0.dp,
                                    minOf(maxWidth - PlayerHorizontalPadding * 2, maxHeight),
                                )
                            val coverShape = RoundedCornerShape(24.dp) // 재생 중 일시정지 버튼 곡률

                            if (hidePlayerThumbnail) {
                                Box(
                                    contentAlignment = Alignment.Center,
                                    modifier =
                                        Modifier
                                            .size(coverSize)
                                            .clip(coverShape)
                                            .background(MaterialTheme.colorScheme.surfaceVariant),
                                ) {
                                    Icon(
                                        painter = painterResource(R.drawable.small_icon),
                                        contentDescription = null,
                                        modifier = Modifier.size(48.dp),
                                        tint = textButtonColor.copy(alpha = 0.7f),
                                    )
                                }
                            } else {
                                AsyncImage(
                                    model = mediaMetadata?.thumbnailUrl,
                                    contentDescription = null,
                                    contentScale = ContentScale.Crop,
                                    modifier =
                                        Modifier
                                            .size(coverSize)
                                            .clip(coverShape),
                                )
                            }
                        }

                        mediaMetadata?.let {
                            controlsContent(it)
                        }
                    }
                }"""


def main():
    path = find_player()
    with open(path, encoding="utf-8", newline="") as f:
        src = f.read().replace("\r\n", "\n")

    if MARK in src:
        sys.exit("이미 패치된 파일이에요. (중복 적용 방지)")

    # 1) import 추가
    imp = "import androidx.compose.foundation.layout.Box\n"
    if imp not in src:
        sys.exit("[실패] Box import 위치를 못 찾았어요.")
    src = src.replace(
        imp, imp + "import androidx.compose.foundation.layout.BoxWithConstraints\n", 1
    )

    # 2) isLandscape 변수 추가 (controlsContent 정의 바로 위)
    anchor = "val controlsContent: @Composable ColumnScope.(MediaMetadata) -> Unit = { mediaMetadata ->"
    if anchor not in src:
        sys.exit("[실패] controlsContent 위치를 못 찾았어요.")
    src = src.replace(
        anchor,
        "val isLandscape = LocalConfiguration.current.orientation == Configuration.ORIENTATION_LANDSCAPE\n        "
        + anchor,
        1,
    )

    # 3) 헤더(제목/아티스트/버튼) 앞에 가로모드 분기 열기
    open_pat = re.compile(
        r'Row\(\s*horizontalArrangement = Arrangement\.SpaceBetween,\s*'
        r'verticalAlignment = Alignment\.CenterVertically,\s*'
        r'modifier =\s*Modifier\s*\.fillMaxWidth\(\)\s*'
        r'\.padding\(horizontal = PlayerHorizontalPadding\),\s*\) \{\s*'
        r'AnimatedContent\(\s*targetState = showInlineLyrics,\s*label = "ThumbnailAnimation",'
    )
    m = open_pat.search(src)
    if not m:
        sys.exit("[실패] 제목/아티스트 헤더 Row 위치를 못 찾았어요.")
    src = src[: m.start()] + HEADER_LANDSCAPE + " else {\n" + src[m.start():]

    # 4) 헤더 분기 닫기 (슬라이더 시작 직전)
    close_pat = re.compile(
        r'\n[ \t]*Spacer\(Modifier\.height\(24\.dp\)\)\s*when \(sliderStyle\) \{'
    )
    m = close_pat.search(src)
    if not m:
        sys.exit("[실패] 슬라이더 시작 위치를 못 찾았어요.")
    src = src[: m.start()] + "\n}" + src[m.start():]

    # 5) 가로모드 전체 레이아웃 교체
    start_pat = re.compile(
        r'Row\(\s*modifier =\s*Modifier\s*'
        r'\.windowInsetsPadding\(\s*'
        r'WindowInsets\.systemBars\.only\(WindowInsetsSides\.Horizontal\)\.add\(verticalWindowInsets\),\s*'
        r'\)\.padding\(bottom = 24\.dp\)\s*\.fillMaxSize\(\),\s*\) \{'
    )
    ms = start_pat.search(src)
    if not ms:
        sys.exit("[실패] 가로모드 Row 시작 위치를 못 찾았어요.")
    end_pat = re.compile(
        r'\n[ \t]*\}\s*\n\s*else -> \{\s*val bottomPadding by animateDpAsState'
    )
    me = end_pat.search(src, ms.end())
    if not me:
        sys.exit("[실패] 가로모드 블록 끝 위치를 못 찾았어요.")
    src = src[: ms.start()] + LANDSCAPE_BODY + src[me.start():]

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    print(f"패치 완료: {path}")


if __name__ == "__main__":
    main()
