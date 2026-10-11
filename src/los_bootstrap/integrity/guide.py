"""Static guidance for making integrity-gated apps usable, alternatives first.

The ordering is deliberate: the routes that change nothing about the phone
come before the ones that do, and spoofing comes last. The three mandatory
warnings (fragility, liability shift, root attack surface) are defined here
and printed by both `integrity guide` and `integrity install`.
"""

from __future__ import annotations

# Mandatory warnings. Printed verbatim wherever spoofing is described or
# performed. Keep these blunt; a recommendation without a downside is a bug.
WARNINGS: tuple[tuple[str, str], ...] = (
    (
        "Fragility",
        "Google revokes spoofed fingerprints regularly. Spoofing can stop "
        "working overnight — possibly when you need the app most, such as "
        "while travelling or doing time-critical banking. Always keep a "
        "non-phone fallback for anything that matters.",
    ),
    (
        "Liability shift",
        "Bank and eID terms of service may place fraud liability on you if "
        "the device was modified. Spoofing hides the modification from the "
        "app; it does not remove the modification, and it does not make the "
        "phone safer.",
    ),
    (
        "Root attack surface",
        "Spoofing requires root, and root plus third-party modules run with "
        "full privileges. Every module you install is code you are trusting "
        "with everything on the phone.",
    ),
)


GUIDE_STEPS: tuple[tuple[str, str], ...] = (
    (
        "1. Use a route that is not the app",
        "The lowest-risk fix changes nothing on the phone. Most German "
        "services have a browser portal or a desktop program: online banking "
        "in a browser (chipTAN with a card reader), Mein ELSTER on a desktop, "
        "the AusweisApp desktop client with a USB card reader, the TK and "
        "other ePA web portals. Check `los-bootstrap integrity compat` for "
        "the alternative listed per app.",
    ),
    (
        "2. Install microG",
        "Apps that only call Google Play APIs (maps, push, login) but do not "
        "check a Play Integrity verdict often work once microG is installed. "
        "This is not spoofing and needs no root. It does not help an app that "
        "requires an actual integrity verdict.",
    ),
    (
        "3. Keep a second device for the few hard blockers",
        "For the handful of apps that refuse every workaround — some ePA and "
        "TAN apps enforce hardware attestation — a cheap stock-firmware phone "
        "used only for those apps avoids compromising your main device.",
    ),
    (
        "4. Use a ROM that can relock the bootloader",
        "If an app requires hardware-backed attestation, the honest fix is a "
        "ROM that supports verified boot with its own key so the phone can be "
        "relocked and pass attestation legitimately — e.g. GrapheneOS on "
        "Pixels (the TK app explicitly allows it), and some CalyxOS and /e/OS "
        "devices. This is a real locked state, not spoofing. Relocking wipes "
        "data and is unsafe on ROMs that do not support it.",
    ),
    (
        "5. Get root (prerequisite for spoofing — guidance only)",
        "Spoofing needs root, which this tool does not automate. The usual "
        "route: extract your boot or init_boot image, patch it in the Magisk "
        "app, and flash the patched image with `fastboot flash`. "
        "`los-bootstrap flash` covers the manufacturer-specific fastboot "
        "steps. You run the destructive flash yourself.",
    ),
    (
        "6. Spoofing (last resort)",
        "Once rooted, a fingerprint-spoofing Magisk/KernelSU module can make "
        "the phone present a certified-device profile so the basic Play "
        "Integrity levels pass, and a DenyList/Zygisk hide feature can keep "
        "apps from detecting root. Some ROMs ship this built in. The "
        "strongest hardware-backed verdict cannot be spoofed this way; that "
        "needs a genuinely locked, attested device (step 4). This tool never "
        "deals in attestation keyboxes. Install a module you downloaded with "
        "`los-bootstrap integrity install` (coming in a later release).",
    ),
)
