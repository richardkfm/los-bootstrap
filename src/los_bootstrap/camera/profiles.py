"""Static, human-maintained GCam port profiles per device.

Add only entries that reflect genuine user reports or personal testing.
Do not generate plausible-sounding but unverified entries.
"""

from __future__ import annotations

from typing import Tuple

from .models import CameraPort, CameraProfile, XmlConfig


CAMERA_PROFILES: Tuple[CameraProfile, ...] = (

    # ── Google Pixel 7 (panther) ──────────────────────────────────────────────
    CameraProfile(
        codename="panther",
        display_name="Google Pixel 7",
        notes=(
            "Pixel 7 has first-class LineageOS 21 support. The Tensor G2 ISP is "
            "fully utilised by LMC 8.4 without GMS. Night Sight and Astrophotography "
            "work on the native Pixel camera stack included in LineageOS for Pixel."
        ),
        ports=(
            CameraPort(
                name="LMC 8.4 R17",
                package="com.google.android.GoogleCamera",
                source_hint=(
                    "Download LMC 8.4 R17 for panther from celsoazevedo.com or your "
                    "device XDA thread. Stage as 'lmc84.apk' in --apk-dir. "
                    "GCam APKs are proprietary; never auto-fetched."
                ),
                verified=True,
                notes=(
                    "Works out-of-the-box on Pixel 7 / LineageOS 21. "
                    "Enable Video Stabilisation: Motion > Stabilisation > Locked. "
                    "Disable Frequent Faces (People & Pets) to improve privacy posture."
                ),
                xml_configs=(
                    XmlConfig(
                        filename="Pixel7_LMC84_default.xml",
                        device_path="/sdcard/GCam/Config/",
                        description=(
                            "Balanced default config for Pixel 7; accurate colours, "
                            "fast autofocus, Night Sight enabled."
                        ),
                        apply_hint=(
                            "adb push Pixel7_LMC84_default.xml /sdcard/GCam/Config/ "
                            "then open LMC 8.4 > ⋮ > Configs > Load."
                        ),
                    ),
                ),
            ),
        ),
    ),

    # ── Google Pixel 6 (oriole) ───────────────────────────────────────────────
    CameraProfile(
        codename="oriole",
        display_name="Google Pixel 6",
        notes=(
            "Pixel 6 is well-supported by LineageOS 21. The Tensor G1 ISP is "
            "fully exposed via camera2 API. LMC 8.4 delivers HDR+ and Night Sight "
            "without GMS."
        ),
        ports=(
            CameraPort(
                name="LMC 8.4 R17",
                package="com.google.android.GoogleCamera",
                source_hint=(
                    "Download LMC 8.4 R17 for oriole from celsoazevedo.com. "
                    "Stage as 'lmc84.apk' in --apk-dir."
                ),
                verified=True,
                notes=(
                    "HDR+ and Night Sight confirmed on LineageOS 21. "
                    "Disable 'Frequent Faces' for better privacy. "
                    "4K 60fps video stable; 4K 30fps preferred for battery life."
                ),
                xml_configs=(
                    XmlConfig(
                        filename="Pixel6_LMC84_default.xml",
                        device_path="/sdcard/GCam/Config/",
                        description=(
                            "Default config for Pixel 6; optimised for Tensor G1 ISP. "
                            "Balanced colours, Night Sight tuned for main sensor."
                        ),
                        apply_hint=(
                            "adb push Pixel6_LMC84_default.xml /sdcard/GCam/Config/ "
                            "then open LMC 8.4 > ⋮ > Configs > Load."
                        ),
                    ),
                ),
            ),
        ),
    ),

    # ── Xiaomi Redmi Note 10 (sunny) ─────────────────────────────────────────
    CameraProfile(
        codename="sunny",
        display_name="Xiaomi Redmi Note 10",
        notes=(
            "Redmi Note 10 (Snapdragon 678) has LineageOS 20 support. "
            "GCam ports improve low-light performance substantially over the "
            "stock camera app. BSG 9.3 is the most reliable port for this SoC."
        ),
        ports=(
            CameraPort(
                name="BSG 9.3.020",
                package="com.google.android.GoogleCamera",
                source_hint=(
                    "Download BSG GCam 9.3 for Snapdragon 678 from "
                    "celsoazevedo.com/files/android/google-camera/dev-bsg/. "
                    "Stage as 'bsg930.apk' in --apk-dir."
                ),
                verified=True,
                notes=(
                    "Wide-angle camera switches correctly with the supplied XML. "
                    "Portrait mode functional. Macro camera requires a separate "
                    "camera2 workaround; see device XDA thread for details. "
                    "4K video limited to 30fps on this SoC."
                ),
                xml_configs=(
                    XmlConfig(
                        filename="RedmiNote10_BSG93_wide.xml",
                        device_path="/sdcard/GCam/Config/",
                        description=(
                            "Enables wide-angle and portrait mode on Redmi Note 10 "
                            "(Snapdragon 678). Tuned for accurate skin tones."
                        ),
                        apply_hint=(
                            "adb push RedmiNote10_BSG93_wide.xml /sdcard/GCam/Config/ "
                            "then open BSG GCam > ⋮ > Configs > Load."
                        ),
                    ),
                ),
            ),
            CameraPort(
                name="LMC 8.4 R17",
                package="com.google.android.GoogleCamera",
                source_hint=(
                    "Download LMC 8.4 for Snapdragon 678 from celsoazevedo.com. "
                    "Stage as 'lmc84.apk' in --apk-dir."
                ),
                verified=False,
                notes=(
                    "LMC 8.4 runs on Redmi Note 10 but wide-angle switching is "
                    "inconsistent without a device-specific XML config. "
                    "BSG 9.3 is the preferred port for this device."
                ),
                xml_configs=(),
            ),
        ),
    ),

    # ── OnePlus 9 (lemonade) ──────────────────────────────────────────────────
    CameraProfile(
        codename="lemonade",
        display_name="OnePlus 9",
        notes=(
            "OnePlus 9 has LineageOS 21 support. Camera2 API must be enabled: "
            "Settings > Camera > Advanced > Camera API: Camera2. "
            "Hasselblad colour processing is bypassed by GCam ports — colours are "
            "Google-tuned rather than OnePlus-tuned; this is expected behaviour."
        ),
        ports=(
            CameraPort(
                name="BSG 9.3.020",
                package="com.google.android.GoogleCamera",
                source_hint=(
                    "Download BSG GCam 9.3 for Snapdragon 888 from "
                    "celsoazevedo.com/files/android/google-camera/dev-bsg/. "
                    "Stage as 'bsg930.apk' in --apk-dir."
                ),
                verified=True,
                notes=(
                    "All three lenses (main, ultra-wide, telephoto) work with the "
                    "supplied XML. 4K 60fps video confirmed stable. "
                    "Disable 'Social Share' option in GCam settings to avoid "
                    "unnecessary Google account prompts."
                ),
                xml_configs=(
                    XmlConfig(
                        filename="OnePlus9_BSG93_default.xml",
                        device_path="/sdcard/GCam/Config/",
                        description=(
                            "Tuned for Snapdragon 888; enables all three lenses on "
                            "OnePlus 9. Balanced exposure and white balance."
                        ),
                        apply_hint=(
                            "adb push OnePlus9_BSG93_default.xml /sdcard/GCam/Config/ "
                            "then open BSG GCam > ⋮ > Configs > Load."
                        ),
                    ),
                ),
            ),
        ),
    ),

    # ── Fairphone 4 (FP4) ─────────────────────────────────────────────────────
    CameraProfile(
        codename="FP4",
        display_name="Fairphone 4",
        notes=(
            "Fairphone 4 is an officially supported LineageOS 21 target. "
            "DivestOS also supports FP4. Full camera2 API is available, "
            "making GCam ports straightforward. Macro and depth sensors "
            "have limited camera2 exposure on some builds."
        ),
        ports=(
            CameraPort(
                name="LMC 8.4 R17",
                package="com.google.android.GoogleCamera",
                source_hint=(
                    "Download LMC 8.4 R17 for Snapdragon 750G from celsoazevedo.com. "
                    "Stage as 'lmc84.apk' in --apk-dir."
                ),
                verified=True,
                notes=(
                    "Main and ultra-wide cameras supported. Night Sight works well "
                    "with the default config. Macro sensor not switchable through "
                    "GCam UI; use the stock camera for macro shots."
                ),
                xml_configs=(
                    XmlConfig(
                        filename="FP4_LMC84_default.xml",
                        device_path="/sdcard/GCam/Config/",
                        description=(
                            "Default config for FP4; balanced for main and wide lenses "
                            "on Snapdragon 750G. Night Sight tuned for low-light."
                        ),
                        apply_hint=(
                            "adb push FP4_LMC84_default.xml /sdcard/GCam/Config/ "
                            "then open LMC 8.4 > ⋮ > Configs > Load."
                        ),
                    ),
                ),
            ),
        ),
    ),

    # ── Xiaomi Mi 11 Lite 5G (renoir) ────────────────────────────────────────
    CameraProfile(
        codename="renoir",
        display_name="Xiaomi Mi 11 Lite 5G",
        notes=(
            "Mi 11 Lite 5G (Snapdragon 780G) confirmed working with LMC 8.4 on "
            "LineageOS. Tested by a contributor running LMC 8.4 with an XML config "
            "from celsoazevedo.com. Profile added from real-world usage report."
        ),
        ports=(
            CameraPort(
                name="LMC 8.4 R17",
                package="com.google.android.GoogleCamera",
                source_hint=(
                    "Download LMC 8.4 R17 for Snapdragon 780G from celsoazevedo.com. "
                    "Stage as 'lmc84.apk' in --apk-dir."
                ),
                verified=True,
                notes=(
                    "Confirmed working on Mi 11 Lite 5G / LineageOS. "
                    "Use the Snapdragon 780G XML config from the same page on "
                    "celsoazevedo.com as the APK download."
                ),
                xml_configs=(
                    XmlConfig(
                        filename="<780G config from celsoazevedo.com>",
                        device_path="/sdcard/GCam/Config/",
                        description=(
                            "Snapdragon 780G XML config from celsoazevedo.com. "
                            "Exact filename varies by LMC 8.4 build; use the config "
                            "linked on the same page as the APK download."
                        ),
                        apply_hint=(
                            "adb push <config>.xml /sdcard/GCam/Config/ "
                            "then open LMC 8.4 > ⋮ > Configs > Load."
                        ),
                    ),
                ),
            ),
        ),
    ),

)
