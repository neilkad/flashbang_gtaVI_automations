"""Scheduled GTA VI Shorts with sourced facts, original graphics, and AI disclosure."""

from dataclasses import dataclass
from datetime import date, datetime
import json
import os
from pathlib import Path
import re
import time

from .video import create_thumbnail, create_video
from .youtube import TOKEN_FILE, set_thumbnail, upload_video


RELEASE_DATE = date(2026, 11, 19)
PRELAUNCH_LAST_DAY = date(2026, 11, 18)
ROCKSTAR_RELEASE = "https://www.rockstargames.com/VI"
ROCKSTAR_PRELOAD = (
    "https://support.rockstargames.com/articles/7nPqOA2uCbpEQHXx7KVrYd/"
    "grand-theft-auto-vi-pre-load-faq"
)
ROCKSTAR_PLATFORMS = (
    "https://support.rockstargames.com/articles/4QfG4FmZCf5W1gS8jy4UVT/"
    "grand-theft-auto-vi-platform-editions-and-versions"
)
ROCKSTAR_NEWSWIRE = "https://www.rockstargames.com/newswire/article/89834o94713o21/pre-load-grand-theft-auto-vi-now"
ROCKSTAR_MEDIA = "https://www.rockstargames.com/VI/media"


@dataclass(frozen=True)
class ContentPlan:
    title: str
    hook: str
    voiceover: str
    beats: tuple[tuple[str, str, str], ...]
    hashtags: tuple[str, ...]
    sources: tuple[str, ...]


def _countdown_plan(day: date) -> ContentPlan:
    days = (RELEASE_DATE - day).days
    return ContentPlan(
        title=f"GTA VI Is {days} Days Away — Check This First",
        hook="GTA VI is almost here. Do not leave this check until launch night.",
        voiceover=(
            f"GTA VI is {days} days away, and the most useful launch detail is not a rumour. "
            "Rockstar says the game releases at midnight local time on November 19 for both PlayStation 5 and Xbox Series X and S. "
            "Digital pre-loading is already open for pre-orders, so check that your console has started the download now. "
            "Do not assume your countdown matches another region. Check your own local release time, then make sure your download queue is ready before launch night."
        ),
        beats=(
            ("COUNTDOWN", f"{days} DAYS TO GO", "Neon Vice City countdown card"),
            ("RELEASE", "NOVEMBER 19", "Calendar transition over original neon coast art"),
            ("TIME", "MIDNIGHT LOCAL TIME", "Clock graphic with regional glow"),
            ("CHECK", "OPEN DOWNLOAD QUEUE", "Console download checklist card"),
        ),
        hashtags=("#GTA6", "#GTAVI", "#GamingShorts", "#PlayStation5", "#XboxSeriesX"),
        sources=(ROCKSTAR_RELEASE, ROCKSTAR_PRELOAD),
    )


def _afternoon_plan(day: date) -> ContentPlan:
    plans = {
        14: ContentPlan(
            "GTA VI Preload Is Here — The 212GB Check You Need",
            "Your GTA VI preload may be ready, but your storage might not be.",
            "GTA VI preload is now available for digital pre-orders, and Rockstar’s official FAQ gives one number you need to check: up to 212 gigabytes of free space, depending on your device. Before launch week gets busy, open your console storage and make room. On PlayStation 5, keep auto-downloads on and use Rest Mode. On Xbox, automatic updates and Sleep mode help the preload finish. The useful move is simple: start the download now, then verify it is actually complete.",
            (("STORAGE", "UP TO 212 GB", "Storage meter over original neon car art"), ("PS5", "REST MODE + AUTO DOWNLOAD", "PS5 preparation checklist card"), ("XBOX", "SLEEP + AUTO UPDATES", "Xbox preparation checklist card"), ("FINAL CHECK", "VERIFY DOWNLOAD COMPLETED", "Green completion graphic")),
            ("#GTA6", "#GTAVI", "#GamingSetup", "#PS5", "#XboxSeriesX"),
            (ROCKSTAR_PRELOAD,),
        ),
        15: ContentPlan(
            "Your GTA VI Preload Could Fail Without This PS5 Setting",
            "If you are on PS5, this one setting decides whether GTA VI preloads while you sleep.",
            "If you pre-ordered GTA VI on PlayStation 5, Rockstar says automatic pre-load needs two things: auto-downloads enabled and your console powered on or in Rest Mode. That means buying the game is not enough if your download settings are off. Open your PS5 settings tonight, confirm auto-downloads are enabled, and leave enough free space for the download. GTA VI releases November 19 at midnight local time, so this is a better check to make now than during a launch-night rush.",
            (("PS5 CHECK", "AUTO DOWNLOADS ON", "Original neon controller dashboard"), ("POWER", "USE REST MODE", "Rest Mode moon icon card"), ("STORAGE", "MAKE SPACE NOW", "Storage bar animation"), ("RELEASE", "NOVEMBER 19", "Calendar reveal")),
            ("#GTA6", "#GTAVI", "#PS5", "#GamingTips", "#GamingShorts"),
            (ROCKSTAR_PRELOAD, ROCKSTAR_RELEASE),
        ),
        16: ContentPlan(
            "GTA VI Xbox Preload Has One Big Difference",
            "Xbox and PlayStation did not start GTA VI preloads at the same local time.",
            "Here is the GTA VI preload difference that can trip people up. Rockstar says PlayStation 5 digital preloads begin at midnight local time on November 10. Xbox Series X and S preloads began globally at 12 a.m. GMT. The game itself still releases at midnight local time on November 19 for both platforms. So if your friend saw the Xbox download first, that does not change your own release time. Check your console queue, your storage, and Rockstar’s regional guide before launch.",
            (("PLAYSTATION", "MIDNIGHT LOCAL TIME", "Local time clock graphic"), ("XBOX", "12 A.M. GMT", "GMT world clock graphic"), ("RELEASE", "MIDNIGHT LOCAL", "Launch clock card"), ("CHECK", "QUEUE + STORAGE", "Original neon checklist")),
            ("#GTA6", "#GTAVI", "#XboxSeriesX", "#PS5", "#GamingNews"),
            (ROCKSTAR_PRELOAD, ROCKSTAR_RELEASE),
        ),
        17: ContentPlan(
            "That GTA VI Physical Box Has a Surprise Inside",
            "Buying GTA VI physically? Rockstar says there is an important thing missing from the box.",
            "The GTA VI physical edition has a launch-week twist. Rockstar’s official platform guide says the box contains a download code, not a disc. The physical Standard Edition is expected to be available from November 12 so players can redeem the code and preload. Rockstar also says a physical Ultimate Edition is not available. So if you are choosing physical, treat it like a code purchase: make sure the code matches your platform account region, redeem it when you receive it, and check that the digital download has started.",
            (("PHYSICAL EDITION", "DOWNLOAD CODE INSIDE", "Stylized game box with digital-code icon"), ("NO DISC", "NO DISC INCLUDED", "Disc icon fades into code symbol"), ("PRELOAD", "REDEEM AND DOWNLOAD", "Step-by-step card"), ("REGION", "MATCH YOUR ACCOUNT", "Globe and account checklist")),
            ("#GTA6", "#GTAVI", "#GamingNews", "#PS5", "#XboxSeriesX"),
            (ROCKSTAR_PLATFORMS,),
        ),
        18: ContentPlan(
            "GTA VI Unlocks Tomorrow — Your Local Time Matters",
            "GTA VI unlocks tomorrow, but a global countdown can still show the wrong time for you.",
            "GTA VI releases tomorrow, November 19, and Rockstar says the launch time is midnight local time in all regions for PlayStation 5 and Xbox Series X and S. That is why copying a countdown from another country can send you to your console at the wrong time. Open Rockstar’s regional release guide, check your own location, and make sure the preload is complete. If your download is still pending, do not wait until midnight to notice it. Launch night is close, so the boring checks are now the important ones.",
            (("TOMORROW", "NOVEMBER 19", "Neon calendar flips to launch day"), ("RELEASE TIME", "MIDNIGHT LOCAL", "Regional clock wheel"), ("PRELOAD", "VERIFY COMPLETE", "Download completion badge"), ("FINAL CHECK", "USE YOUR TIME ZONE", "Glowing globe card")),
            ("#GTA6", "#GTAVI", "#GamingNews", "#PS5", "#XboxSeriesX"),
            (ROCKSTAR_RELEASE, ROCKSTAR_PRELOAD),
        ),
    }
    return plans[day.day]


def _evening_plan(day: date) -> ContentPlan:
    plans = {
        14: ContentPlan(
            "GTA VI's 30 FPS Target: The Official Reason",
            "GTA VI is targeting 30 frames per second, and Rockstar explained what it is spending that power on.",
            "Rockstar says GTA VI is targeting 30 frames per second on the current console generation while pushing both systems to their limits. The official explanation focuses on the density and visual fidelity of Leonida’s environments and inhabitants. That is a useful detail because it sets expectations before launch: Rockstar is prioritising the scale and look of the world at that target. The real test comes when players have the game in their hands, but the 30 FPS target is Rockstar’s stated plan today.",
            (("OFFICIAL TARGET", "30 FPS", "Bold performance meter graphic"), ("WHY", "WORLD DENSITY", "Original neon city density visual"), ("FOCUS", "VISUAL FIDELITY", "Cinematic color-gradient card"), ("SOURCE", "ROCKSTAR NEWSWIRE", "Official-source stamp")),
            ("#GTA6", "#GTAVI", "#GamingNews", "#PS5", "#XboxSeriesX"),
            (ROCKSTAR_NEWSWIRE,),
        ),
        15: ContentPlan(
            "GTA VI's 30 FPS Target Has One Clear Reason",
            "Before launch, Rockstar has already explained why GTA VI is aiming for 30 FPS.",
            "Rockstar’s latest preload announcement says GTA VI targets 30 frames per second on the current generation of consoles. Their stated reason is the ambition of Leonida: dense environments and inhabitants with high visual fidelity. That does not tell us every performance detail, but it does tell us Rockstar’s design priority before launch. If you are comparing expectations across PlayStation 5 and Xbox Series X and S, use Rockstar’s own wording first, then wait for real launch-day analysis instead of treating speculation as fact.",
            (("ROCKSTAR SAYS", "TARGETING 30 FPS", "Performance dial over neon boulevard"), ("PRIORITY", "DENSE LEONIDA", "City lights and palm silhouettes"), ("FOCUS", "VISUAL FIDELITY", "Cinematic lens frame"), ("WAIT FOR", "LAUNCH-DAY ANALYSIS", "Official-source checker")),
            ("#GTA6", "#GTAVI", "#GamingNews", "#PS5", "#XboxSeriesX"),
            (ROCKSTAR_NEWSWIRE,),
        ),
        16: ContentPlan(
            "GTA VI on PS5 Pro: What Rockstar Actually Confirmed",
            "There is one GTA VI PS5 Pro detail Rockstar has actually put in writing.",
            "Rockstar’s official preload announcement says the PlayStation 5 Pro version of GTA VI includes improved clarity through PlayStation Spectral Super Resolution, also called PSSR, plus ray-traced shadows that Rockstar says are only available on PS5 Pro. That is the confirmed detail. It does not tell us to invent frame-rate claims or other upgrades, so keep the conversation anchored to what Rockstar has said. If you are choosing a platform for launch, that is the PS5 Pro feature list Rockstar has confirmed so far.",
            (("PS5 PRO", "PSSR CLARITY", "Original neon skyline sharpness graphic"), ("SHADOWS", "RAY-TRACED SHADOWS", "Stylized light-and-shadow card"), ("CONFIRMED", "ROCKSTAR NEWSWIRE", "Official source badge"), ("AVOID", "UNVERIFIED CLAIMS", "Fact check symbol")),
            ("#GTA6", "#GTAVI", "#PS5Pro", "#GamingNews", "#GamingShorts"),
            (ROCKSTAR_NEWSWIRE,),
        ),
        17: ContentPlan(
            "GTA VI's New Official Screenshots Are Waiting Here",
            "Before launch, Rockstar has posted a new official GTA VI gallery to look through.",
            "If you want a GTA VI refresh without chasing leaks, Rockstar posted an official launch gallery on November 5. The gallery is on the GTA VI site, alongside the new official news and launch material. That matters because it gives fans a verified place to look at new screenshots instead of relying on reposts with missing context. Visit Rockstar’s GTA VI page, open the launch gallery, and treat it as the source. With launch this close, official screenshots are more useful than a random rumour thread.",
            (("OFFICIAL GALLERY", "NEW LAUNCH SCREENSHOTS", "Original neon photo-gallery card"), ("SOURCE", "ROCKSTAR'S GTA VI SITE", "Verified-source stamp"), ("AVOID", "RUMOUR REPOSTS", "Blurred social post fades away"), ("CHECK", "THE LAUNCH GALLERY", "Neon gallery navigation card")),
            ("#GTA6", "#GTAVI", "#GamingNews", "#GamingShorts", "#ViceCity"),
            (ROCKSTAR_RELEASE,),
        ),
        18: ContentPlan(
            "GTA VI Is One Day Away — Check Your Platform",
            "GTA VI is nearly here, and this is the platform check you should make before midnight.",
            "GTA VI launches tomorrow on PlayStation 5 and Xbox Series X and S. That is the official platform list Rockstar has published for release, so make sure you have the game attached to the right console account before the countdown ends. For digital buyers, confirm the preload completed. For physical buyers, remember Rockstar says the box has a download code rather than a disc. The best launch-night plan is simple: correct account, enough storage, finished download, and your local release time saved.",
            (("PLATFORMS", "PS5 + XBOX SERIES X|S", "Dual-platform launch card"), ("DIGITAL", "PRELOAD COMPLETE?", "Download checkmark"), ("PHYSICAL", "CODE, NOT DISC", "Code card graphic"), ("LAUNCH", "MIDNIGHT LOCAL", "Neon launch clock")),
            ("#GTA6", "#GTAVI", "#GamingNews", "#PS5", "#XboxSeriesX"),
            (ROCKSTAR_RELEASE, ROCKSTAR_PLATFORMS),
        ),
    }
    return plans[day.day]


def _night_plan(day: date) -> ContentPlan:
    """Fourth daily slot: a distinct, source-backed pre-launch angle."""
    plans = {
        15: ContentPlan(
            "GTA VI’s 212GB Warning Is Real — Check This Tonight",
            "Four days before launch, one storage number can still stop your GTA VI preload.",
            "Four days before GTA VI unlocks, Rockstar has one storage warning worth checking tonight: the preload can need up to 212 gigabytes, depending on your console. That space has to exist before the download can finish. Open your storage screen, clear room, then confirm the GTA VI download shows as complete. A flashy launch countdown does not help if your queue is stuck at ninety percent. Make the space now and let the preload finish before launch night.",
            (("STORAGE ALERT", "UP TO 212 GB", "Storage meter over official GTA VI clip"), ("CHECK NOW", "CLEAR THE SPACE", "Console storage checklist"), ("PRELOAD", "VERIFY 100%", "Download completion frame"), ("LAUNCH", "NOVEMBER 19", "Vice City countdown graphic")),
            ("#GTA6", "#GTAVI", "#GamingNews", "#PS5", "#XboxSeriesX"),
            (ROCKSTAR_PRELOAD,),
        ),
        16: ContentPlan(
            "GTA VI’s Official Vault Has 138 Screenshots — Stop Trusting Fake Clips",
            "Before believing another GTA VI leak, Rockstar has given fans a fast fact-check.",
            "GTA VI leaks are everywhere, but Rockstar’s official media vault gives fans a faster fact-check. The page lists nine downloadable video clips, 138 screenshots, and 27 artwork and wallpaper downloads, all from the official source. It also points to the launch gallery, trailer, and extended look. So when a supposed new GTA VI image appears on your feed, compare it with Rockstar’s vault first. If the source cannot be found there, treat it as unverified, not confirmed.",
            (("OFFICIAL VAULT", "ROCKSTAR'S MEDIA LIBRARY", "Fast official clip montage"), ("SCREENSHOTS", "138 OFFICIAL IMAGES", "Gallery-style crop sequence"), ("VIDEO", "9 OFFICIAL CLIPS", "Character clip montage"), ("CHECK FIRST", "SKIP FAKE LEAKS", "Verified-source badge")),
            ("#GTA6", "#GTAVI", "#ViceCity", "#GamingNews", "#GamingShorts"),
            (ROCKSTAR_MEDIA,),
        ),
        17: ContentPlan(
            "GTA VI’s Release Clock Can Trick You — Don’t Copy Another Country",
            "One GTA VI countdown can be right for your friend and wrong for you.",
            "GTA VI is two days away, and the release clock can still catch players out. Rockstar says the game unlocks at midnight local time on November 19 for PlayStation 5 and Xbox Series X and S. That means another country’s countdown can be wrong for your console. Check your own local time, make sure the preload finished, and do not wait until launch night to discover a region or storage problem. Vice City is close, but your own clock is the one that matters.",
            (("2 DAYS TO GO", "YOUR CLOCK MATTERS", "Neon countdown over official clip"), ("UNLOCK", "MIDNIGHT LOCAL", "Regional clock graphic"), ("PLATFORMS", "PS5 + XBOX SERIES X|S", "Dual platform frame"), ("CHECK", "PRELOAD COMPLETE?", "Launch-night checklist")),
            ("#GTA6", "#GTAVI", "#GamingNews", "#PS5", "#XboxSeriesX"),
            (ROCKSTAR_RELEASE, ROCKSTAR_PRELOAD),
        ),
        18: ContentPlan(
            "GTA VI Unlocks Tomorrow — This Is Your Last Safe Checklist",
            "One day remains. These three checks decide whether you play at midnight.",
            "GTA VI unlocks tomorrow, so this is the last calm moment to check your launch setup. Rockstar says the game releases at midnight local time on PlayStation 5 and Xbox Series X and S. Digital players should confirm the preload is complete and that enough storage remains. Physical buyers should remember Rockstar says the box uses a download code rather than a disc. Correct account, finished download, enough space, local release time. Get those four right now, and launch night becomes much easier.",
            (("ONE DAY LEFT", "LAST SAFE CHECK", "Launch countdown over official clip"), ("DIGITAL", "PRELOAD COMPLETE?", "Download verification graphic"), ("PHYSICAL", "CODE, NOT DISC", "Digital-code card"), ("UNLOCK", "MIDNIGHT LOCAL", "Neon clock reveal")),
            ("#GTA6", "#GTAVI", "#GamingNews", "#GamingShorts", "#ViceCity"),
            (ROCKSTAR_RELEASE, ROCKSTAR_PRELOAD, ROCKSTAR_PLATFORMS),
        ),
    }
    return plans[day.day]


def _late_plan(day: date) -> ContentPlan:
    if day != date(2026, 11, 14):
        raise ValueError("The late slot is only available for November 14, 2026.")
    return ContentPlan(
        title="GTA VI’s Official Media Vault Just Opened",
        hook="Vice City leaks are flying, but Rockstar just gave you the fastest way to spot the fakes.",
        voiceover=(
            "Vice City leaks are flying, but Rockstar just gave GTA VI fans the fastest way to spot the fakes. "
            "The official media vault now holds nine downloadable clips, 138 screenshots, and 27 artwork and wallpaper downloads. "
            "It also links to the launch gallery, the trailer, and the extended look. So when a so-called new GTA VI clip hits your feed, check the real source first. "
            "If it is not in Rockstar’s vault, it is not official news."
        ),
        beats=(
            ("OFFICIAL MEDIA", "ROCKSTAR'S GTA VI LIBRARY", "Official clip montage and media-page screen recording"),
            ("VIDEO CLIPS", "9 OFFICIAL CLIPS", "Fast character and cover-art clip montage"),
            ("SCREENSHOTS", "138 OFFICIAL IMAGES", "Screenshot-gallery scroll and full-screen crop"),
            ("CHECK FIRST", "SKIP THE FAKE LEAKS", "Source-page URL and verified badge"),
        ),
        hashtags=("#GTA6", "#GTAVI", "#GamingNews", "#ViceCity", "#GamingShorts"),
        sources=(ROCKSTAR_MEDIA,),
    )


XBOX_CLOUD = "https://news.xbox.com/en-us/2026/11/10/grand-theft-auto-6-comes-to-xbox-cloud-gaming-november-19/"


def _news_plan(day: date) -> ContentPlan:
    return ContentPlan(
        title="GTA VI Just Got a Big Launch Update — Even Xbox One Can Play",
        hook="GTA VI just got a launch update that changes who can play on day one.",
        voiceover=(
            "GTA VI just got a launch update that changes who can play on day one. "
            "Xbox says the game will also stream through Xbox Cloud Gaming on Xbox One and Xbox Series X and S, starting at 1 a.m. Eastern on November nineteenth. "
            "Cloud play uses Xbox Series S graphics settings. Microsoft also calls GTA VI the most pre-ordered title of all time on its store, and says pre-loading is open now. "
            "Pre-order the Ultimate Edition before November nineteenth ends, and it includes the Vintage Vice City Pack and one month of GTA Plus. "
            "So which way are you playing: native console or cloud?"
        ),
        beats=(
            ("CLOUD PLAY", "XBOX ONE CAN STREAM IT", "Neon cloud-streaming console card"),
            ("DAY ONE", "1 AM ET, NOV 19", "Neon launch clock reveal"),
            ("DEMAND", "MOST PRE-ORDERED ON MS STORE", "Pre-order counter bar graphic"),
            ("BONUS", "VINTAGE VICE CITY PACK", "Ultimate Edition bonus badge"),
        ),
        hashtags=("#GTA6", "#GTAVI", "#GamingNews", "#XboxCloudGaming", "#GamingShorts"),
        sources=(XBOX_CLOUD, ROCKSTAR_RELEASE),
    )


def _cloud_settings_plan(day: date) -> ContentPlan:
    return ContentPlan(
        title="GTA VI on Xbox Cloud: The Graphics Catch Most People Miss",
        hook="Before you stream GTA VI on cloud, know this one graphics catch.",
        voiceover=(
            "Before you stream GTA VI on Xbox Cloud Gaming, know this one catch. Xbox says cloud play uses Xbox Series S graphics settings. "
            "Series X and Series S can play it natively and pre-install now, while Xbox One players stream it. "
            "Streaming starts at 1 a.m. Eastern on November nineteenth. "
            "So if you want the best Xbox picture, native Series X is the way. Which one are you picking?"
        ),
        beats=(
            ("CLOUD CATCH", "SERIES S GRAPHICS SETTINGS", "Neon graphics-settings card"),
            ("NATIVE", "SERIES X AND S PRE-INSTALL", "Console pre-install badge"),
            ("XBOX ONE", "STREAMS VIA CLOUD", "Cloud streaming console card"),
            ("START TIME", "1 AM ET, NOV 19", "Neon clock reveal"),
        ),
        hashtags=("#GTA6", "#GTAVI", "#XboxCloudGaming", "#GamingNews", "#GamingShorts"),
        sources=(XBOX_CLOUD,),
    )


def _cloud_access_plan(day: date) -> ContentPlan:
    return ContentPlan(
        title="No Game Pass? You Can Still Stream GTA VI on Xbox Cloud",
        hook="No Game Pass? Xbox just opened a door for GTA VI.",
        voiceover=(
            "No Game Pass? Xbox just opened a door for GTA VI. Starting November eleventh, players in supported markets can buy cloud playtime to stream supported games without a Game Pass subscription. "
            "GTA VI must still be purchased separately, and availability can vary by market and device. "
            "Xbox also says more Rockstar games, including GTA V and Red Dead Redemption 2, are coming to cloud gaming in the coming months. "
            "Check if your market is supported, then tell me in the comments what you would play first."
        ),
        beats=(
            ("NO GAME PASS", "BUY CLOUD PLAYTIME", "Neon cloud-ticket card"),
            ("CHECK", "SUPPORTED MARKETS ONLY", "Region availability badge"),
            ("BUY GAME", "GTA VI SOLD SEPARATELY", "Store price-tag card"),
            ("COMING SOON", "GTA V AND RDR2 ON CLOUD", "Rockstar library card"),
        ),
        hashtags=("#GTA6", "#GTAVI", "#XboxCloudGaming", "#RedDeadRedemption2", "#GamingShorts"),
        sources=(XBOX_CLOUD,),
    )


GTA_V_PAGE = "https://www.rockstargames.com/gta-v"


def _vs_release_plan(day: date) -> ContentPlan:
    return ContentPlan(
        title="GTA 5 vs GTA 6: 13 Years Apart",
        hook="GTA 5 vs GTA 6: here is what thirteen years changes.",
        voiceover=(
            "GTA 5 versus GTA 6, side by side. GTA 5 launched in September 2013 on PlayStation 3 and Xbox 360. "
            "GTA 6 lands on November 19, 2026, on PlayStation 5 and Xbox Series X and S. "
            "That is a thirteen year gap, and the biggest wait in the series. Which one are you playing first? Drop it in the comments."
        ),
        beats=(
            ("RELEASE", "SEPTEMBER 2013 // NOVEMBER 19 2026", "VS"),
            ("CONSOLES", "PS3 AND XBOX 360 // PS5 AND XBOX SERIES X S", "VS"),
            ("THE WAIT", "13 YEARS SINCE LAUNCH // 4 DAYS LEFT", "VS"),
        ),
        hashtags=("#GTA6", "#GTA5", "#GTAVI", "#GamingShorts", "#Comparison"),
        sources=(ROCKSTAR_RELEASE, GTA_V_PAGE),
    )


def _vs_heroes_plan(day: date) -> ContentPlan:
    return ContentPlan(
        title="GTA 5 vs GTA 6: Heroes Face Off",
        hook="Three heroes against two. Who wins?",
        voiceover=(
            "GTA 5 gave you three playable heroes: Michael, Franklin and Trevor. "
            "GTA 6 is built around two: Lucia and Jason, a duo in Rockstar's first trailer. "
            "More heroes, or a tighter duo? Tell me which you prefer in the comments."
        ),
        beats=(
            ("HEROES", "3 PLAYABLE LEADS // 2 LEADS: LUCIA AND JASON", "VS"),
            ("NAMES", "MICHAEL FRANKLIN TREVOR // LUCIA AND JASON", "VS"),
            ("YOUR PICK", "TEAM OF THREE? // OR A DUO?", "VS"),
        ),
        hashtags=("#GTA6", "#GTA5", "#Lucia", "#GamingShorts", "#Comparison"),
        sources=(ROCKSTAR_RELEASE, GTA_V_PAGE),
    )


def _vs_world_plan(day: date) -> ContentPlan:
    return ContentPlan(
        title="GTA 5 vs GTA 6: Los Santos or Vice City?",
        hook="Los Santos or Vice City? Pick a side.",
        voiceover=(
            "GTA 5 took place in Los Santos and the state of San Andreas. "
            "GTA 6 moves to the state of Leonida, with Vice City at its heart. "
            "Sunny LA energy, or neon Vice City nights? Choose your city in the comments."
        ),
        beats=(
            ("THE STATE", "SAN ANDREAS // LEONIDA", "VS"),
            ("THE CITY", "LOS SANTOS // VICE CITY", "VS"),
            ("YOUR CITY", "SUNNY LOS SANTOS? // NEON VICE CITY?", "VS"),
        ),
        hashtags=("#GTA6", "#GTA5", "#ViceCity", "#GamingShorts", "#Comparison"),
        sources=(ROCKSTAR_RELEASE, GTA_V_PAGE),
    )


def _vs_series_plan(day: date) -> ContentPlan:
    return ContentPlan(
        title="GTA 1 to GTA 6: Every Game Explained in 60 Seconds",
        hook="Every mainline GTA from 1997 to 2026, in one minute.",
        voiceover=(
            "Every mainline GTA, in one minute. GTA 1, in 1997, was a top-down game spread across three cities. "
            "GTA 2, in 1999, set its chaos in a near future. "
            "GTA 3, in 2001, took the series into full 3D in Liberty City. "
            "GTA 4, in 2008, returned to Liberty City with a gritty, realistic look. "
            "GTA 5, in 2013, gave us Los Santos and three heroes. "
            "And GTA 6 arrives on November 19, 2026, in Leonida. Which one is your all time favourite?"
        ),
        beats=(
            ("GTA 1", "1997 // TOP-DOWN, THREE CITIES", "SERIES"),
            ("GTA 2", "1999 // NEAR-FUTURE CHAOS", "SERIES"),
            ("GTA 3", "2001 // FIRST FULL 3D, LIBERTY CITY", "SERIES"),
            ("GTA 4", "2008 // GRITTY LIBERTY CITY", "SERIES"),
            ("GTA 5", "2013 // LOS SANTOS, THREE HEROES", "SERIES"),
            ("GTA 6", "NOV 19 2026 // LEONIDA", "SERIES"),
        ),
        hashtags=("#GTA6", "#GTA5", "#GTA", "#GamingShorts", "#GTAHistory"),
        sources=(ROCKSTAR_RELEASE, GTA_V_PAGE),
    )


def _meme_wait_plan(day: date) -> ContentPlan:
    return ContentPlan(
        title="Me Waiting For GTA 6 Meme",
        hook="POV: you waiting for GTA 6.",
        voiceover=(
            "POV: you have been waiting for GTA 6 since twenty thirteen. "
            "Your friends said it is almost here. Your wallet said it is time. "
            "Your sleep schedule said, bro, no. Four days left. Tag the friend who will not sleep on launch night."
        ),
        beats=(
            ("WAITING", "ME: I'LL SLEEP EARLY // GTA 6 AT MIDNIGHT: LOL NO", "MEME"),
            ("PRELOAD", "ME CHECKING PRELOAD // FOR THE 40TH TIME TODAY", "MEME"),
            ("FRIENDS", "FRIEND: IS IT OUT YET? // ME: 4 DAYS. STOP ASKING", "MEME"),
        ),
        hashtags=("#GTA6", "#Meme", "#GamingMemes", "#GTAVI", "#Shorts"),
        sources=(ROCKSTAR_RELEASE,),
    )


def _meme_launch_plan(day: date) -> ContentPlan:
    return ContentPlan(
        title="GTA 6 Launch Night Meme",
        hook="Launch night, but make it chaos.",
        voiceover=(
            "Launch night at midnight, and the whole squad is online. "
            "One friend is still downloading. One friend forgot to preload. "
            "And you? You already picked your snacks. Which one are you? Comment it."
        ),
        beats=(
            ("DOWNLOAD", "EVERYONE AT MIDNIGHT // ME: STILL AT 3 PERCENT", "MEME"),
            ("SNACKS", "GTA 6 LAUNCHES // ME: SNACKS READY, PHONE OFF", "MEME"),
            ("WHICH ONE", "THE PRELOADER? OR // THE LAST MINUTE PANICKER?", "MEME"),
        ),
        hashtags=("#GTA6", "#Meme", "#GamingMemes", "#LaunchNight", "#Shorts"),
        sources=(ROCKSTAR_RELEASE,),
    )


_NATIVE_HINGLISH = (
    "GTA 6 Preload Kaise Karein", "Standard ya Ultimate", "Kis Desh Mein Kab Aayega",
    "GTA 1 Se GTA 6 Ki Kahani", "13 Saal Kyun Lage",
    "RDR2 vs GTA 6", "3 Bade Open Worlds", "System Requirements Kya", "PS4 Par Chalega",
    "GTA 6 vs ", "Wallet Meme", "Wanted Level Meme", "Midnight Meme", "Is Channel Par Kya Milega",
)


def _hg_download_plan(day: date) -> ContentPlan:
    return ContentPlan(
        title="GTA 6 Preload Kaise Karein (Step by Step)",
        hook="GTA 6 preload kaise karna hai? Bas 3 steps.",
        voiceover=(
            "GTA Six preload karna chahte ho? Bas teen steps. "
            "Pehla, apne PlayStation ya Xbox ke store mein GTA Six pre order dhundo. "
            "Doosra, pre order karne ke baad preload ka option on karo, aur download queue mein game daalo. "
            "Teesra, console ki storage pehle se khaali rakho, taaki launch night par download atak na jaye. "
            "Rockstar ke mutabiq game November unnees ko release hoga, aur digital preload pre order walon ke liye khula hai."
        ),
        beats=(
            ("STEP 1", "STORE MEIN GTA 6 PRE-ORDER DHUNDO", "console store"),
            ("STEP 2", "PRELOAD ON KARO, DOWNLOAD QUEUE MEIN DAALO", "preload"),
            ("STEP 3", "STORAGE KHAALI RAKHO LAUNCH SE PEHLE", "storage"),
        ),
        hashtags=("#GTA6", "#GTAVI", "#Preload", "#HowTo", "#GamingShorts"),
        sources=(ROCKSTAR_RELEASE,),
    )


def _hg_editions_plan(day: date) -> ContentPlan:
    return ContentPlan(
        title="GTA 6 Standard ya Ultimate Edition? Kaunsa Lein",
        hook="GTA 6: Standard ya Ultimate? Pehle yeh dekho.",
        voiceover=(
            "GTA Six ke do editions hain, Standard aur Ultimate Edition. "
            "Standard mein poora game milta hai, seedha aur simple. "
            "Ultimate Edition mein Rockstar extra content deta hai, jaise special gaadiyan, weapons, gear aur tattoo. "
            "Agar tumhe bas story chahiye, Standard kaafi hai. "
            "Aur agar extras aur collection pasand hain, Ultimate dekho. Tum kaunsa loge? Comment mein batao."
        ),
        beats=(
            ("STANDARD", "POORA GAME, SIMPLE AUR SEEDHA", "pro"),
            ("ULTIMATE", "EXTRA GAADIYAN WEAPONS GEAR AUR TATTOO", "pro"),
            ("TERA PICK", "STORY CHAHIYE? STANDARD. EXTRAS? ULTIMATE", "pick"),
        ),
        hashtags=("#GTA6", "#GTAVI", "#UltimateEdition", "#Editions", "#GamingShorts"),
        sources=(ROCKSTAR_RELEASE,),
    )


def _hg_countries_plan(day: date) -> ContentPlan:
    return ContentPlan(
        title="GTA 6 Kis Desh Mein Kab Aayega? Apna Time Check Karo",
        hook="GTA 6 tumhare desh mein kab aayega?",
        voiceover=(
            "GTA Six kis desh mein kab aayega? Rockstar ne kaha hai ki game November unnees ko aadhi raat, "
            "yaani midnight local time par release hoga. "
            "Matlab har desh mein apni raat barah baje. India mein bhi apne midnight par, aur doosre desh mein unke midnight par. "
            "Isliye kisi aur desh ka countdown dekh kar confuse mat ho. Apna local time check karo, aur download pehle se ready rakho."
        ),
        beats=(
            ("RELEASE", "19 NOVEMBER MIDNIGHT LOCAL TIME", "time"),
            ("TUMHARA DESH", "HAR DESH MEIN APNI RAAT 12 BAJE", "time"),
            ("TIP", "APNA LOCAL TIME CHECK KARO", "time"),
        ),
        hashtags=("#GTA6", "#GTAVI", "#ReleaseTime", "#India", "#GamingShorts"),
        sources=(ROCKSTAR_RELEASE,),
    )


def _hg_story_plan(day: date) -> ContentPlan:
    return ContentPlan(
        title="GTA 1 Se GTA 6 Ki Kahani: Poori Series 60 Second Mein",
        hook="GTA 1 se GTA 6 tak: poori kahani.",
        voiceover=(
            "GTA ki kahani ek se shuru hui, saal unnees sau satanve mein. "
            "Phir GTA Two aaya unnees sau ninyanve mein. "
            "GTA Three ne do hazaar ek mein poori series ki dishaa badal di, ek 3D open world ke saath. "
            "GTA Four aaya do hazaar aath mein, aur GTA Five September do hazaar terah mein, "
            "jo saalon tak chalta raha. Ab GTA Six, November unnees do hazaar chhabbis ko, "
            "Vice City ki taraf Leonida mein lautne wala hai."
        ),
        beats=(
            ("GTA 1", "1997: YAHAN SE SHURUAAT", "story"),
            ("GTA 2", "1999: SERIES AAGE BADHI", "story"),
            ("GTA 3", "2001: 3D OPEN WORLD KA DAUR", "story"),
            ("GTA 4", "2008: NAYA MOOD AUR NAYA DAUR", "story"),
            ("GTA 5", "SEPT 2013: SAALON TAK CHALA", "story"),
            ("GTA 6", "19 NOV 2026: LEONIDA AUR VICE CITY", "story"),
        ),
        hashtags=("#GTA6", "#GTAVI", "#GTAHistory", "#GTA", "#GamingShorts"),
        sources=(ROCKSTAR_RELEASE, GTA_V_PAGE),
    )


def _hg_wait_plan(day: date) -> ContentPlan:
    return ContentPlan(
        title="GTA 6 Ko 13 Saal Kyun Lage? Jo Pata Hai Woh Yeh Hai",
        hook="GTA 6 ko 13 saal kyun lage?",
        voiceover=(
            "GTA Five September do hazaar terah mein aaya tha, aur GTA Six November do hazaar chhabbis mein aa raha hai. "
            "Terah saal ka gap. Rockstar ne exact wajah officially nahi batayi, isliye jo kehna hai woh bas andaaza hai. "
            "Itna pata hai ki GTA Five ka naya console par safar saalon tak chala, "
            "aur ab GTA Six do nayi generation ke baad PlayStation Five aur Xbox Series par aa raha hai. "
            "Tumhe kya lagta hai, intezaar worth hoga? Comment mein batao."
        ),
        beats=(
            ("2013", "GTA 5 AAYA SEPT 2013 MEIN", "gap"),
            ("13 SAAL", "RESEARCH KA GAP, WAJAH OFFICIAL NAHI", "gap"),
            ("2026", "PS5 AUR XBOX SERIES PAR AA RAHA HAI", "gap"),
        ),
        hashtags=("#GTA6", "#GTAVI", "#13Years", "#Rockstar", "#GamingShorts"),
        sources=(ROCKSTAR_RELEASE, GTA_V_PAGE),
    )


RDR2_PAGE = "https://www.rockstargames.com/reddeadredemption2"


def _plan_of(title, hook, voice, beats, tags, sources=None):
    return ContentPlan(title=title, hook=hook, voiceover=voice, beats=beats, hashtags=tags, sources=sources or (ROCKSTAR_RELEASE,))


def _rdr_vs_plan(day: date) -> ContentPlan:
    return _plan_of(
        "RDR2 vs GTA 6 Kaun Sa Bada Hai",
        "RDR2 ya GTA 6, kaun sa bada?",
        "Red Dead Redemption Two aur GTA Six, dono Rockstar ke. RDR2 aaya october do hazaar atharah mein, GTA Six aa raha hai november do hazaar chhabbis mein. "
        "RDR2 ki kahani unnees sau se pehle ke Wild West mein hai, aur GTA Six aaj ke zamane ke Leonida mein, jahan Vice City hai. "
        "RDR2 mein ek hero, Arthur Morgan. GTA Six mein do, Lucia aur Jason. Tumhara pick kaun sa? Comment mein batao.",
        (("RELEASE", "OCTOBER 2018 // NOVEMBER 19 2026", "VS"),
         ("ERA", "1899 WILD WEST // MODERN DAY LEONIDA", "VS"),
         ("HEROES", "ARTHUR MORGAN // LUCIA AND JASON", "VS")),
        ("#GTA6", "#RDR2", "#Rockstar", "#GamingShorts", "#Comparison"), (ROCKSTAR_RELEASE, RDR2_PAGE))


def _rdr_timeline_plan(day: date) -> ContentPlan:
    return _plan_of(
        "Rockstar Ke 3 Bade Open Worlds",
        "Rockstar ke teen bade open worlds.",
        "Rockstar ke teen sabse bade open world games. GTA Five, do hazaar terah. Red Dead Redemption Two, do hazaar atharah. Aur ab GTA Six, do hazaar chhabbis. "
        "Har ek ke beech saalon ka intezaar. Pehle do ke baad ab sabki nazar GTA Six par hai. Tumhara favourite kaun sa hai? Comment karo.",
        (("2013", "GTA 5, 13 SAAL PEHLE", "gap"),
         ("2018", "RED DEAD REDEMPTION 2, WILD WEST", "gap"),
         ("2026", "GTA 6, 19 NOVEMBER", "gap")),
        ("#GTA6", "#RDR2", "#GTA5", "#Rockstar", "#GamingShorts"), (ROCKSTAR_RELEASE, GTA_V_PAGE, RDR2_PAGE))


def _specs_plan(day: date) -> ContentPlan:
    return _plan_of(
        "GTA 6 System Requirements Kya Hain",
        "GTA 6 chalane ke liye kya chahiye?",
        "GTA Six chalane ke liye kya chahiye? Rockstar ke mutabiq game PlayStation Five aur Xbox Series X aur S par aa raha hai. "
        "PC version abhi announce nahi hua, isliye PC ki official minimum requirements bhi nahi hain. Jo koi PC specs bata raha hai, woh andaaza hai. "
        "Console par bas ek PS5 ya Xbox Series chahiye, aur preload ke liye storage khaali rakho. Rockstar ka size aur update official page par dekhna.",
        (("PS5", "PLAYSTATION 5 PAR AA RAHA HAI", "console"),
         ("XBOX", "XBOX SERIES X AUR S PAR BHI", "console"),
         ("PC?", "PC ABHI ANNOUNCE NAHI, SPECS BHI NAHI", "pc")),
        ("#GTA6", "#SystemRequirements", "#PS5", "#Xbox", "#GamingShorts"), (ROCKSTAR_RELEASE, ROCKSTAR_NEWSWIRE))


def _ps4_plan(day: date) -> ContentPlan:
    return _plan_of(
        "Kya GTA 6 PS4 Par Chalega",
        "Kya GTA 6 purane PS4 par chalega?",
        "Kya GTA Six PS4 ya Xbox One par chalega? Rockstar ke mutabiq nahi. Game sirf PlayStation Five aur Xbox Series X aur S ke liye hai. "
        "Agar tumhare paas purana console hai, toh ek option Xbox Cloud Gaming hai, jo Xbox ne november unnees ke liye announce kiya hai. "
        "Plan banao, aur comment mein batao tumhare paas kaun sa console hai.",
        (("PS4?", "PS4 AUR XBOX ONE PAR NAHI", "console"),
         ("OK", "SIRF PS5 AUR XBOX SERIES X S", "console"),
         ("CLOUD", "XBOX CLOUD GAMING 19 NOVEMBER", "cloud")),
        ("#GTA6", "#PS4", "#PS5", "#Xbox", "#GamingShorts"), (ROCKSTAR_RELEASE, XBOX_CLOUD))


def _meme3_plan(day: date) -> ContentPlan:
    return _plan_of(
        "GTA 6 Wallet Meme",
        "Mera wallet vs GTA 6.",
        "Mera wallet: bhai, rehne de. Mera dimaag: GTA Six aa raha hai. Wallet: kaun sa GTA? Dimaag: woh wala. Wallet: jaa raha hoon. "
        "Tag karo us dost ko jo launch par bhi udhaar maangega.",
        (("WALLET", "WALLET: BHAI REHNE DE // ME: GTA 6 AA RAHA HAI", "MEME"),
         ("SALARY", "SALARY AAYI // GTA 6 PRE-ORDER: HELLO", "MEME"),
         ("FRIEND", "DOST: UDHAAR DE DE // ME: PEHLE GTA 6", "MEME")),
        ("#GTA6", "#Meme", "#GamingMemes", "#Funny", "#Shorts"))


def _meme4_plan(day: date) -> ContentPlan:
    return _plan_of(
        "GTA 6 Wanted Level Meme",
        "Pehle hi minute mein wanted level?",
        "Launch ke baad ka plan: story mission karunga. Asli plan: pehle hi minute mein kuch kar dunga aur police peeche. "
        "Mission? Kaun sa mission? Tag karo us dost ko jo story chhod kar bas ghoomta rahega.",
        (("PLAN", "PLAN: STORY MISSION // REALITY: WANTED LEVEL", "MEME"),
         ("POLICE", "POLICE: RUK JA // ME: KYUN RUKUN", "MEME"),
         ("MISSION", "MISSION: START // ME: BAAD MEIN KARUNGA", "MEME")),
        ("#GTA6", "#Meme", "#WantedLevel", "#GamingMemes", "#Shorts"))


def _meme5_plan(day: date) -> ContentPlan:
    return _plan_of(
        "GTA 6 Midnight Meme",
        "Midnight par kaun kaun jaag raha hai?",
        "Raat ke barah baje. Mummy: so ja. Main: bas ek minute. Ek minute baad: GTA Six ka download pachaas percent. "
        "Subah ka alarm: kaun si subah? Comment karo, tum kitne baje tak jaagoge.",
        (("MUMMY", "MUMMY: SO JA // ME: BAS EK MINUTE", "MEME"),
         ("DOWNLOAD", "DOWNLOAD 50 PERCENT // ME: ISKE BINA NAHI SOUNGA", "MEME"),
         ("ALARM", "SUBAH KA ALARM // ME: KAUN SI SUBAH", "MEME")),
        ("#GTA6", "#Meme", "#LaunchNight", "#GamingMemes", "#Shorts"))


def _expect_plan(day: date) -> ContentPlan:
    return _plan_of(
        "Is Channel Par Kya Milega",
        "Is channel par kya milega? Sach batata hoon.",
        "Is channel par kya milega? Bina bakwaas commentary ke, sirf game. Koi chehra nahi, koi faltu gyaan nahi. "
        "Launch ke baad yahan GTA Six gameplay aayega, jisme main fumble bhi karunga, maara bhi jaunga, par maza pakka hai. Yeh awaaz AI hai, meri nahi. "
        "Subscribe karo, aur bata do pehle kya dekhna chahte ho.",
        (("KYA MILEGA", "SIRF GAME, BINA BAKWAAS COMMENTARY", "gap"),
         ("NO FACE", "CHEHRA NAHI, SIRF GAMEPLAY", "gap"),
         ("PAKKA", "FUMBLE BHI, DEATH BHI, MAZA PAKKA", "gap")),
        ("#GTA6", "#GamingShorts", "#SPECTREGaming", "#GTAVI", "#Subscribe"))


def _fresh(day: date) -> list[ContentPlan]:
    return [_rdr_vs_plan(day), _specs_plan(day), _meme3_plan(day), _expect_plan(day),
            _rdr_timeline_plan(day), _ps4_plan(day), _meme4_plan(day), _meme5_plan(day), *_vs_rival_plans(day)]


def _bank(day: date) -> list[ContentPlan]:
    return [
        _news_plan(day),
        _countdown_plan(day),
        _cloud_settings_plan(day),
        _afternoon_plan(day),
        _cloud_access_plan(day),
        _evening_plan(day),
        _vs_release_plan(day),
        _night_plan(day),
        _vs_heroes_plan(day),
        _vs_world_plan(day),
        _vs_series_plan(day),
        _meme_wait_plan(day),
        _meme_launch_plan(day),
        _hg_download_plan(day),
        _hg_editions_plan(day),
        _hg_countries_plan(day),
        _hg_story_plan(day),
        _hg_wait_plan(day),
    ]


def _plan(day: date, slot: str) -> ContentPlan:
    match = re.fullmatch(r"h(\d\d)", slot)
    if match:
        bank = _bank(day)
        return bank[(int(match.group(1)) + day.day) % len(bank)]
    if re.fullmatch(r"q\d+", slot):
        from . import news
        item = news.load_plan(slot)
        if item:
            beats = tuple(tuple(part.strip() for part in line.split("|"))[:3] for line in item["beats"])
            beats = tuple(b if len(b) == 3 else (b[0], b[-1], "gap") for b in beats)
            tags = tuple(item.get("hashtags") or ("#GTA6", "#GTAVI"))
            return ContentPlan(title=item["title"], hook=item.get("hook") or item["title"], voiceover=item["voiceover"],
                               beats=beats, hashtags=tags, sources=(item["source_link"], ROCKSTAR_RELEASE))
        order = _fresh(day) + _bank(day)
        return order[max(int(slot[1:]) - 4, 0) % len(order)]
    hg = {"g1": _hg_download_plan, "g2": _hg_editions_plan, "g3": _hg_countries_plan, "g4": _hg_story_plan, "g5": _hg_wait_plan}
    if slot in hg:
        return hg[slot](day)
    if slot == "m1":
        return _meme_wait_plan(day)
    if slot == "m2":
        return _meme_launch_plan(day)
    if slot == "vs1":
        return _vs_release_plan(day)
    if slot == "vs2":
        return _vs_heroes_plan(day)
    if slot == "vs4":
        return _vs_series_plan(day)
    if slot == "vs3":
        return _vs_world_plan(day)
    if slot == "morning":
        return _countdown_plan(day)
    if slot == "afternoon":
        return _afternoon_plan(day)
    if slot == "evening":
        return _evening_plan(day)
    if slot == "night":
        return _night_plan(day)
    if slot == "news":
        return _news_plan(day)
    if slot == "late":
        return _late_plan(day)
    if slot == "remix":
        return _late_plan(day)
    if slot == "trailer":
        return _late_plan(day)
    raise ValueError("Slot must be 'morning', 'afternoon', 'evening', 'night', 'late', 'remix', or 'trailer'.")


def _state_path(day: date, slot: str) -> Path:
    return Path("output/daily") / f"{day.isoformat()}-{slot}.json"


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _write_script(day: date, slot: str, plan: ContentPlan) -> Path:
    script_path = Path("output/scripts") / f"{day.strftime('%Y%m%d')}-{slot}-gta-vi.md"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    beats = "\n".join(f"- {label} | {copy} | {visual}" for label, copy, visual in plan.beats)
    description = (
        "Official GTA VI launch update and practical prep information.\n\n"
        "AI disclosure: The script, voice, music, captions and graphics in this video are AI-generated. Unofficial fan channel, not affiliated with or endorsed by Rockstar Games or Take-Two Interactive. Footage is from Rockstar Games' official media (c) Rockstar Games / Take-Two. SPECTRE Gaming selected the topic and checked the claims against the linked sources."
    )
    script_path.write_text(
        "\n".join((
            "# SPECTRE Gaming — sourced GTA VI launch update",
            "",
            f"## Title\n{plan.title}",
            f"\n## Hook\n{plan.hook}",
            f"\n## Voiceover\n{plan.voiceover}",
            f"\n## Visual beats\n{beats}",
            "\n## On-screen captions\nTimed captions are rendered from the voiceover.",
            f"\n## Description\n{description}",
            f"\n## Hashtags\n{' '.join(plan.hashtags)}",
            f"\n## Sources\n{'\n'.join(plan.sources)}",
            "\n## Fact check before recording\nAll factual claims were limited to the linked Rockstar sources.",
            "",
        )),
        encoding="utf-8",
    )
    return script_path


def _section(markdown: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}[^\n]*\n(.*?)(?=^##\s|\Z)",
        markdown,
        flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


_AI_DISCLOSURE = (
    "AI disclosure: Is video ki script, awaaz, music, captions aur graphics AI se bane hain. Yeh ek unofficial fan channel hai, Rockstar Games ya Take-Two Interactive se judaa ya unka endorsed nahi hai. Footage Rockstar Games ke official media se hai (c) Rockstar Games / Take-Two."
)


_AI_DISCLOSURE_EN = (
    "AI disclosure: The script, voice, music, captions and graphics in this video are AI-generated. Unofficial fan channel, not affiliated with or endorsed by Rockstar Games or Take-Two Interactive. Footage is from Rockstar Games' official media (c) Rockstar Games / Take-Two."
)


PROMO_SOCIAL = "Follow @flashbangfumbles on Instagram, Facebook and YouTube for daily GTA 6 updates."
PROMO = ("Subscribe: https://www.youtube.com/@flashbangfumbles | Instagram: @flashbangfumbles | "
         "Facebook: facebook.com/FlashbangFumbles")


def _is_english_slot(slot: str) -> bool:
    """Queue slots alternate languages from q005 on: odd = pure English, even = Hinglish."""
    match = re.fullmatch(r"q(\d+)", slot)
    return bool(match) and int(match.group(1)) >= 5 and int(match.group(1)) % 2 == 1


def _make_english(script_path: Path) -> None:
    """Rewrite a script as natural, pure English (title, thumbnail, hook, voiceover, beats)."""
    markdown = script_path.read_text(encoding="utf-8")
    if "<!-- english -->" in markdown:
        return
    beats = _section(markdown, "Visual beats")
    prompt = (
        "Rewrite this GTA VI YouTube Short script in natural, punchy, PURE ENGLISH (no Hindi or Hinglish words). "
        "Keep every fact, number and name exactly; add no new facts. Make the title clickbait but truthful, under 70 characters, "
        "with one emoji at the end. Return ONLY JSON: "
        '{"title": "...", "thumbnail": "2-4 WORDS UPPERCASE", "hook": "...", "voiceover": "...", "beats": ["label | detail | visual", ...]} '
        "with the same number and order of beats; UPPERCASE the label and detail; keep the visual field and any '//' separators unchanged. "
        "Do not include any call to action in the voiceover.\n\n"
        f"TITLE: {_section(markdown, 'Title')}\nHOOK: {_section(markdown, 'Hook')}\n"
        f"VOICEOVER:\n{_section(markdown, 'Voiceover')}\n\nBEATS:\n{beats}"
    )
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=types.HttpOptions(timeout=40_000))
    models = ("gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash", os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
    data = None
    for attempt in range(len(models) * 2):
        try:
            response = client.models.generate_content(
                model=models[attempt % len(models)], contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"))
            data = json.loads(response.text)
            if data.get("title") and data.get("voiceover") and len(data.get("beats", [])) == len([l for l in beats.splitlines() if l.strip()]):
                break
            data = None
        except Exception as error:
            print(f"English rewrite retry {attempt + 1}: {str(error)[:100]}", flush=True)
            time.sleep(2)
    if not data:
        raise RuntimeError("Could not produce the English version; will retry next run.")

    def put(md: str, heading: str, text: str) -> str:
        return re.sub(rf"(^##\s+{re.escape(heading)}[^\n]*\n).*?(?=^##\s|\Z)",
                      lambda m: m.group(1) + text.strip() + "\n\n", md, count=1, flags=re.M | re.S | re.I)

    markdown = put(markdown, "Title", data["title"].strip()[:100])
    markdown = put(markdown, "Hook", data.get("hook", "") or data["title"])
    markdown = put(markdown, "Voiceover", data["voiceover"])
    markdown = put(markdown, "Visual beats", "\n".join(f"- {b.lstrip('- ').strip()}" for b in data["beats"]))
    thumb = (data.get("thumbnail") or "GTA 6").upper()[:28]
    if "## Thumbnail" in markdown:
        markdown = put(markdown, "Thumbnail", thumb)
    else:
        markdown = markdown.replace("\n## Hook", f"\n## Thumbnail\n{thumb}\n\n## Hook", 1)
    markdown = re.sub(r"<!-- hinglish -->\s*", "", markdown)
    script_path.write_text(markdown.rstrip() + "\n\n<!-- english -->\n", encoding="utf-8")


def _localize_script(script_path: Path) -> None:
    """Rewrite the voiceover in Hinglish and the description as natural viewer-facing copy."""
    markdown = script_path.read_text(encoding="utf-8")
    if "<!-- hinglish -->" in markdown or "<!-- english -->" in markdown:
        return
    if any(key in _section(markdown, "Title") for key in _NATIVE_HINGLISH):
        script_path.write_text(markdown.rstrip() + "\n\n<!-- hinglish -->\n", encoding="utf-8")
        return
    import os
    from dotenv import load_dotenv
    from google import genai
    from google.genai import types

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return
    voiceover = _section(markdown, "Voiceover")
    title = _section(markdown, "Title")
    prompt = f"""Rewrite this GTA VI Short for an Indian audience.
Title: {title}
English voiceover: {voiceover}

Return strict JSON with two keys:
"voiceover": the same facts in natural spoken Hinglish (Hindi written in Roman/English letters, mixed with common English gaming words). Keep every fact, number, date and platform exactly as in the English. Same length (about 75-110 words). Sound like a real, excited Indian gaming creator talking to friends: open with a punchy hook in the first sentence, use short conversational sentences ("Bhai", "dekho", "suno" sparingly), build curiosity, and end with one direct question that makes viewers comment (e.g. which platform they will play on). Never mention being an AI, a prompt, a script or a transcript. No emojis, no stage directions.
"description": a 2-3 sentence YouTube description in friendly Hinglish for viewers. It should read like a caption that summarises what the video tells them and why it matters, not like an instruction or a prompt. End the description with the same comment-driving question. No hashtags, no sources, no disclosure."""
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=180_000))
    try:
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        data = json.loads(response.text)
        new_voice = re.sub(r"\s+", " ", data["voiceover"]).strip()
        new_desc = data["description"].strip()
        if len(new_voice.split()) < 40 or not new_desc:
            return
    except Exception as error:
        print(f"Hinglish rewrite skipped: {error}", flush=True)
        return

    def replace(text: str, heading: str, body: str) -> str:
        return re.sub(
            rf"(^##\s+{heading}[^\n]*\n).*?(?=^##\s|\Z)",
            lambda m: m.group(1) + body + "\n\n",
            text, count=1, flags=re.MULTILINE | re.DOTALL,
        )

    markdown = replace(markdown, "Voiceover", new_voice)
    markdown = replace(markdown, "Description", f"{new_desc}\n\n{_AI_DISCLOSURE}")
    script_path.write_text(markdown.rstrip() + "\n\n<!-- hinglish -->\n", encoding="utf-8")


_CTA_HINGLISH = (
    "Aur haan, abhi subscribe karo, like thok do, share karo aur bell icon dabao! "
    "Warna 19 tareekh ko mere GTA Six ke last minute fumble moments miss kar doge, aur phir pachtaoge!"
)
_CTA_ENGLISH = (
    "And hit subscribe, smash like, share it, and ring that bell! "
    "Or you will miss my last-minute GTA Six fumble videos on the nineteenth, and trust me, you will regret it!"
)


_CLICKBAIT = (
    ("RDR2 vs GTA 6", "RDR2 vs GTA 6: Kaun Sa Bada? 🤯", "RDR2 VS GTA 6"),
    ("3 Bade Open Worlds", "Rockstar Ke 3 Bade Open Worlds 🔥", "ROCKSTAR KE 3 WORLDS"),
    ("System Requirements Kya", "GTA 6 Chalane Ke Liye Kya Chahiye? 🎮", "GTA 6 SPECS?"),
    ("PS4 Par Chalega", "Kya GTA 6 PS4 Par Chalega? 😬", "PS4 PAR CHALEGA?"),
    ("Wallet Meme", "Mera Wallet vs GTA 6 😭💀", "WALLET VS GTA 6"),
    ("Wanted Level Meme", "GTA 6 Ke Pehle Minute Mein Wanted Level 💀", "WANTED LEVEL 5"),
    ("Midnight Meme", "GTA 6 Ki Raat Kaun Kaun Jaagega? 😭", "KAUN JAAGEGA?"),
    ("Is Channel Par Kya", "Is Channel Par Kya Milega? (Sach) 🎮", "SIRF GAME. NO FACE."),
    ("Days Away", None, None),
    ("Preload Kaise", "GTA 6 Preload Kaise Karein? 3 Easy Steps ⚡", "PRELOAD KAISE KAREIN?"),
    ("Standard ya Ultimate", "GTA 6: Standard ya Ultimate? Paisa Waste Mat Karo 💸", "STANDARD YA ULTIMATE?"),
    ("Kis Desh Mein", "GTA 6 Tumhare Desh Mein Kab Aayega? ⏰", "TUMHARE DESH MEIN KAB?"),
    ("Ki Kahani", "GTA 1 Se GTA 6: Poori Kahani 🔥", "GTA 1 SE GTA 6"),
    ("13 Saal Kyun", "GTA 6 Ko 13 Saal Kyun Lage? 😱", "13 SAAL KYUN?"),
    ("Me Waiting", "POV: You Waiting For GTA 6 😭 (Too Real)", "POV: GTA 6 WAIT"),
    ("Launch Night Meme", "GTA 6 Launch Night Be Like 💀", "LAUNCH NIGHT BE LIKE"),
    ("Every Game Explained", "GTA 1 to GTA 6: Every Game Explained in 60 Seconds 🔥", "EVERY GTA EVER"),
    ("13 Years Apart", "GTA 5 vs GTA 6: The 13-Year Glow-Up 😱", "GTA 5 VS GTA 6"),
    ("Heroes Face Off", "GTA 5 vs GTA 6: Which Heroes Win? 🔥", "3 HEROES VS 2!"),
    ("Los Santos or Vice", "Los Santos vs Vice City: Pick ONE 🌴", "LOS SANTOS VS VICE CITY"),
    ("Preload Could Fail", "Your GTA 6 Preload Will FAIL If You Skip This 😳", "PRELOAD WILL FAIL?"),
    ("Media Vault", "Stop Sharing FAKE GTA 6 Leaks! Check This First 🚨", "FAKE LEAKS EXPOSED"),
    ("Xbox One Can Play", "Xbox One Can Play GTA 6?! 🤯 Microsoft Just Said It", "XBOX ONE CAN PLAY?!"),
    ("Graphics Catch", "GTA 6 on Xbox Cloud: The Catch Nobody Tells You 👀", "THE CLOUD CATCH"),
    ("No Game Pass", "No Game Pass? You Can STILL Play GTA 6! 🎮", "NO GAME PASS? NO PROBLEM"),
)


def _clickbait(markdown: str) -> str:
    """Swap in a punchy title and add a short thumbnail hook (idempotent)."""
    if "## Thumbnail" in markdown:
        return markdown
    title = _section(markdown, "Title").strip()
    new_title, thumb = f"{title} 😱"[:100], "MUST WATCH"
    days = re.search(r"Is (\d+) Days Away", title)
    if days:
        n = days.group(1)
        new_title, thumb = f"GTA 6 Is {n} DAYS Away 😱 Do THIS Before Launch!", f"{n} DAYS LEFT!"
    for key, t, h in _CLICKBAIT:
        if t and key in title:
            new_title, thumb = t, h
    markdown = markdown.replace(f"## Title\n{title}", f"## Title\n{new_title}", 1)
    return markdown.replace("\n## Hook", f"\n## Thumbnail\n{thumb}\n\n## Hook", 1)


def _append_cta(script_path: Path) -> None:
    markdown = script_path.read_text(encoding="utf-8")
    if "<!-- cta -->" in markdown:
        return
    cta = _CTA_HINGLISH if "<!-- hinglish -->" in markdown else _CTA_ENGLISH
    voiceover = _section(markdown, "Voiceover")
    markdown = re.sub(
        r"(^##\s+Voiceover[^\n]*\n).*?(?=^##\s)",
        lambda m: m.group(1) + f"{voiceover} {cta}\n\n",
        markdown, count=1, flags=re.MULTILINE | re.DOTALL,
    )
    script_path.write_text(markdown.rstrip() + "\n<!-- cta -->\n", encoding="utf-8")


def _archive_short(video_path: Path, day: date, slot: str, title: str, video_id: str) -> None:
    """Keep a local copy of every published Short."""
    import shutil
    folder = Path.home() / "Documents" / "GTA VI" / "Published Shorts"
    folder.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9 ]+", "", title).strip()[:60]
    try:
        shutil.copy2(video_path, folder / f"{day.isoformat()}_{slot}_{safe}_{video_id}.mp4")
    except OSError as error:
        print(f"Archive skipped: {error}", flush=True)


# (name, year, studio, setting, known for)
_RIVALS = (
    ("The Last of Us 2", "2020", "NAUGHTY DOG", "POST-APOCALYPTIC USA", "STORY AND ACTING", "story-driven aur linear hai, open world nahi"),
    ("Witcher 3", "2015", "CD PROJEKT RED", "FANTASY CONTINENT", "QUESTS AND WRITING", "quests aur kahani ke liye mashhoor hai"),
    ("Cyberpunk 2077", "2020", "CD PROJEKT RED", "NIGHT CITY", "FUTURISTIC CITY", "ek bade futuristic sheher mein set hai"),
    ("Elden Ring", "2022", "FROMSOFTWARE", "THE LANDS BETWEEN", "EXPLORATION AND BOSSES", "exploration aur mushkil bosses ke liye jaana jaata hai"),
    ("Skyrim", "2011", "BETHESDA", "FANTASY SKYRIM", "FREEDOM AND MODS", "azaadi aur mods ke liye mashhoor hai"),
    ("Breath of the Wild", "2017", "NINTENDO", "HYRULE", "EXPLORATION FREEDOM", "Hyrule ki khuli duniya mein har jagah jaane ki azaadi deta hai"),
    ("Horizon Zero Dawn", "2017", "GUERRILLA", "ROBOT-FILLED WILDS", "ROBOT HUNTING", "robot janwaron ke shikaar ke liye mashhoor hai"),
    ("Spider-Man", "2018", "INSOMNIAC", "NEW YORK CITY", "WEB SWINGING", "New York mein web swinging ke liye mashhoor hai"),
    ("Ghost of Tsushima", "2020", "SUCKER PUNCH", "FEUDAL JAPAN", "SAMURAI COMBAT", "samurai combat aur Japan ke visuals ke liye mashhoor hai"),
    ("Assassin's Creed Odyssey", "2018", "UBISOFT", "ANCIENT GREECE", "HISTORY AND SCALE", "purane Greece ki badi duniya ke liye mashhoor hai"),
    ("Fallout 4", "2015", "BETHESDA", "POST-WAR BOSTON", "BASE BUILDING", "base building aur post-apocalypse duniya ke liye mashhoor hai"),
)


def _vs_rival_plans(day: date) -> list[ContentPlan]:
    plans = []
    for name, year, studio, setting, famous, line in _RIVALS:
        plans.append(_plan_of(
            f"GTA 6 vs {name}",
            f"GTA 6 ya {name}, kaun sa bada?",
            f"GTA Six versus {name}. {name} {year} mein aaya, {studio.title()} ka game hai, aur {line}. "
            "GTA Six November unnees do hazaar chhabbis ko aa raha hai, aaj ke zamane ke Leonida mein, aur Vice City bhi hai. "
            "Rockstar ne gameplay ka size aur quality ka official comparison nahi diya, toh yeh sirf tumhari pasand ka sawaal hai. "
            f"Tum kise pehle khelte, GTA Six ya {name}? Comment mein batao.",
            (("RELEASE", f"NOVEMBER 19 2026 // {year}", "VS"),
             ("MAKER", f"ROCKSTAR GAMES // {studio}", "VS"),
             ("WORLD", f"LEONIDA AND VICE CITY // {setting}", "VS")),
            ("#GTA6", f"#{re.sub('[^A-Za-z0-9]', '', name)}", "#OpenWorld", "#GamingShorts", "#Comparison"),
            (ROCKSTAR_RELEASE,)))
    return plans


_CLICKBAIT = _CLICKBAIT + tuple(
    (f"GTA 6 vs {r[0]}", f"GTA 6 vs {r[0]}: Kaun Jeetega? 🤯", f"GTA 6 VS {r[0].upper()}"[:28]) for r in _RIVALS
)

_SEO_HASHTAGS = ("#GTA6", "#GTAVI", "#Shorts", "#GrandTheftAutoVI", "#Rockstar", "#GTA6Trailer", "#GTA6News",
                 "#GamingShorts", "#Gaming", "#PS5", "#XboxSeriesX", "#Hinglish", "#ViceCity")
_SEO_TAGS = ("GTA 6", "GTA VI", "GTA 6 release date", "GTA 6 trailer", "GTA 6 news", "GTA 6 Hindi", "GTA 6 Hinglish",
             "Grand Theft Auto VI", "Rockstar Games", "Lucia and Jason", "Vice City", "Leonida", "GTA 6 PS5",
             "GTA 6 Xbox", "GTA 6 gameplay", "GTA 6 countdown", "GTA 6 November 19", "gaming shorts", "shorts")


def _seo(title: str, hashtags: list[str]) -> tuple[str, list[str], list[str]]:
    """Merge topic hashtags with relevant high-reach ones (max 15) and build a tag list under YouTube's 500 chars."""
    merged: list[str] = []
    for tag in [*_SEO_HASHTAGS[:3], *hashtags, *_SEO_HASHTAGS[3:]]:
        if tag.lower() not in {t.lower() for t in merged}:
            merged.append(tag)
    merged = merged[:15]
    if "#" not in title and len(title) + 7 <= 100:
        title = f"{title} #GTA6"
    topic = [t.lstrip("#") for t in hashtags]
    tags: list[str] = []
    for tag in [*topic, *_SEO_TAGS]:
        if tag.lower() not in {t.lower() for t in tags} and sum(len(t) + 1 for t in tags) + len(tag) < 450:
            tags.append(tag)
    return title, merged, tags


def run_daily(slot: str, upload: bool = True, day: date | None = None, visibility: str = "private") -> dict:
    """Prepare one sourced Short and optionally upload it with the requested visibility."""
    day = day or datetime.now().date()
    if day > PRELAUNCH_LAST_DAY:
        raise RuntimeError("This launch schedule ends on November 18, 2026.")
    if day < date(2026, 11, 14):
        raise RuntimeError("This launch schedule starts on November 14, 2026.")
    if visibility not in {"private", "public", "unlisted"}:
        raise ValueError("Visibility must be private, public, or unlisted.")

    plan = _plan(day, slot)
    state_file = _state_path(day, slot)
    state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.is_file() else {}
    script_path = Path(state["script_path"]) if state.get("script_path") else _write_script(day, slot, plan)
    if not script_path.is_file():
        script_path = _write_script(day, slot, plan)
    news_item = None
    if re.fullmatch(r"q\d+", slot):
        from . import news
        news_item = news.load_plan(slot)
    if news_item:
        md = script_path.read_text(encoding="utf-8")
        if "<!-- hinglish -->" not in md and "<!-- english -->" not in md:
            thumb = news_item.get("thumbnail", "GTA 6 NEWS").upper()[:28]
            if "## Thumbnail" not in md:
                md = md.replace("\n## Hook", f"\n## Thumbnail\n{thumb}\n\n## Hook", 1)
            script_path.write_text(md.rstrip() + ("\n\n<!-- english -->\n" if news_item["lang"] == "en" else "\n\n<!-- hinglish -->\n"), encoding="utf-8")
    elif _is_english_slot(slot):
        _make_english(script_path)
    _localize_script(script_path)
    _append_cta(script_path)
    script_path.write_text(_clickbait(script_path.read_text(encoding="utf-8")), encoding="utf-8")
    video_path = Path(state["video_path"]) if state.get("video_path") else None
    if not video_path or not video_path.is_file():
        video_path = create_video(script_path, require_source_media=visibility == "public")

    markdown = script_path.read_text(encoding="utf-8")
    title = re.sub(r"\s+", " ", _section(markdown, "Title")).strip().strip("*`")[:100]
    description = _section(markdown, "Description")
    hashtags = re.findall(r"#[\w]+", _section(markdown, "Hashtags"))
    sources = _section(markdown, "Sources")
    title, hashtags, tags = _seo(title, hashtags)
    description = f"{description}\n\n{PROMO}\n\nSources:\n{sources}\n\n{' '.join(hashtags)}"
    state.update({
        "date": day.isoformat(),
        "slot": slot,
        "privacy": visibility,
        "script_path": str(script_path),
        "video_path": str(video_path),
        "title": title,
        "description": description,
        "tags": tags,
        "ai_disclosure": "AI-assisted scripting, editing, and on-screen graphics are disclosed in the description.",
    })
    _save_state(state_file, state)

    if upload and not state.get("youtube_video_id"):
        if not TOKEN_FILE.is_file():
            raise RuntimeError("YouTube is not connected. Run 'spectre youtube-auth' before enabling scheduled uploads.")
        video_id = upload_video(str(video_path), title, description, state["tags"], visibility=visibility)
        state["youtube_video_id"] = video_id
        try:
            state["thumbnail_set"] = set_thumbnail(video_id, str(create_thumbnail(script_path)))
        except Exception as error:
            print(f"Thumbnail skipped: {error}", flush=True)
        state["youtube_url"] = f"https://youtu.be/{video_id}"
        _save_state(state_file, state)
        _archive_short(video_path, day, slot, state.get("title") or plan.title, video_id)

    if upload and state.get("youtube_video_id"):
        done = state.setdefault("social", {})
        try:
            from . import meta
            if not (done.get("facebook") and done.get("instagram")):
                posted = meta.cross_post(video_path, title, hashtags, PROMO_SOCIAL + '\n\n' + _AI_DISCLOSURE_EN if "<!-- english -->" in markdown else PROMO_SOCIAL + '\n\n' + _AI_DISCLOSURE, skip=tuple(k for k in ('facebook', 'instagram') if done.get(k)))
                for name in ("facebook", "instagram"):
                    if posted.get(name):
                        done[name] = posted[name]
                    done[name + "_error"] = posted.get(name + "_error", "")
                _save_state(state_file, state)
                print(f"Social: {posted}", flush=True)
        except Exception as error:
            print(f"Social posting skipped: {error}", flush=True)

    result = {"script": str(script_path), "video": str(video_path), "state": str(state_file)}
    if state.get("youtube_url"):
        result["youtube_url"] = state["youtube_url"]
    return result
