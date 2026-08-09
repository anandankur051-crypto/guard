"""
Converts the detailed RegTrack pipeline result
into a user-friendly compliance report.
"""


def format_report(report: dict) -> str:

    results = report.get("results", [])

    if not results:
        return (
            "REGTRACK COMPLIANCE REPORT\n\n"
            "No regulatory requirements were identified."
        )

    gaps = []
    conflicts = []
    no_policy = []
    compliant = []

    for result in results:

        status = result.get("status", "").lower()

        item = {
            "explanation": (
                result.get("explanation") or ""
            ).strip(),
            "action": (
                result.get("suggested_edit") or ""
            ).strip(),
        }

        if status == "gap":
            gaps.append(item)

        elif status == "conflict":
            conflicts.append(item)

        elif status == "no_existing_policy":
            no_policy.append(item)

        elif status == "compliant":
            compliant.append(item)

    # ---------------------------------------------------------
    # Remove duplicate findings
    # ---------------------------------------------------------

    def unique(items):

        seen = set()
        output = []

        for item in items:

            key = (
                item["explanation"],
                item["action"]
            )

            if key not in seen:
                seen.add(key)
                output.append(item)

        return output

    gaps = unique(gaps)
    conflicts = unique(conflicts)
    no_policy = unique(no_policy)

    # ---------------------------------------------------------
    # Overall status
    # ---------------------------------------------------------

    if conflicts:
        status = "CONFLICT FOUND"
        icon = "⚠️"

    elif gaps or no_policy:
        status = "ACTION REQUIRED"
        icon = "⚠️"

    else:
        status = "COMPLIANT"
        icon = "✓"

    # ---------------------------------------------------------
    # Report
    # ---------------------------------------------------------

    lines = []

    lines.append("REGTRACK COMPLIANCE REPORT")
    lines.append("=" * 30)
    lines.append("")

    lines.append(f"{icon} {status}")
    lines.append("")

    # ---------------------------------------------------------
    # Overall explanation
    # ---------------------------------------------------------

    if conflicts:

        lines.append(
            f"Your policy appears to conflict with "
            f"{len(conflicts)} regulatory requirement(s)."
        )

    elif gaps or no_policy:

        total = len(gaps) + len(no_policy)

        lines.append(
            f"Your policy requires attention for "
            f"{total} regulatory requirement(s)."
        )

    else:

        lines.append(
            "Your existing policy appears to adequately "
            "cover the identified regulatory requirements."
        )

    lines.append("")

    # ---------------------------------------------------------
    # Conflicts
    # ---------------------------------------------------------

    if conflicts:

        lines.append("WHAT NEEDS ATTENTION")
        lines.append("-" * 30)
        lines.append("")

        for item in conflicts:

            lines.append(
                f"• {item['explanation']}"
            )

            if item["action"]:
                lines.append(
                    f"  Recommended action: {item['action']}"
                )

            lines.append("")

    # ---------------------------------------------------------
    # Policy gaps
    # ---------------------------------------------------------

    if gaps:

        lines.append("POLICY GAPS")
        lines.append("-" * 30)
        lines.append("")

        for item in gaps:

            lines.append(
                f"• {item['explanation']}"
            )

            if item["action"]:
                lines.append(
                    f"  Recommended action: {item['action']}"
                )

            lines.append("")

    # ---------------------------------------------------------
    # Missing policies
    # ---------------------------------------------------------

    if no_policy:

        lines.append("MISSING POLICY COVERAGE")
        lines.append("-" * 30)
        lines.append("")

        # Don't overwhelm the user.
        # Show at most 3 findings.
        for item in no_policy[:3]:

            lines.append(
                f"• {item['explanation']}"
            )

            if item["action"]:
                lines.append(
                    f"  Recommended action: {item['action']}"
                )

            lines.append("")

        remaining = len(no_policy) - 3

        if remaining > 0:

            lines.append(
                f"• {remaining} additional requirement(s) "
                "did not have a relevant policy match."
            )

            lines.append("")

    # ---------------------------------------------------------
    # Compliant
    # ---------------------------------------------------------

    if compliant:

        lines.append("COVERED REQUIREMENTS")
        lines.append("-" * 30)
        lines.append("")

        lines.append(
            f"✓ {len(compliant)} requirement(s) appear to be "
            "adequately covered by your existing policy."
        )

        lines.append("")

    # ---------------------------------------------------------
    # Recommended next step
    # ---------------------------------------------------------

    lines.append("RECOMMENDED NEXT STEP")
    lines.append("-" * 30)
    lines.append("")

    if conflicts:

        lines.append(
            "Review the conflicting policy sections with the "
            "compliance team and align them with the new RBI requirements."
        )

    elif gaps or no_policy:

        lines.append(
            "Review the affected policy sections and update "
            "them to address the identified RBI requirements."
        )

    else:

        lines.append(
            "No immediate policy changes are required. "
            "Continue monitoring future RBI updates."
        )

    return "\n".join(lines)