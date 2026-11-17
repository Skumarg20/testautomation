"""
MargBooks ke source code se locators nikaalo.

    python -m framework.scan_code D:\\margbooks-frontend
    (ya scan-code.bat -- wo path poochh lega)

Ek baar chala do. Uske baad agent ko har screen ke field pehle hi din mil
jayenge -- un screens ke bhi jahan wo kabhi pahuncha hi nahi.
"""
import sys

from framework import code_scanner


def main():
    if len(sys.argv) < 2:
        print("\n  Kaunsa folder scan karna hai?")
        print("  Aise chalao:  python -m framework.scan_code D:\\margbooks-frontend\n")
        return

    path = " ".join(sys.argv[1:]).strip().strip('"')
    print(f"\n=== SOURCE SCAN ===\n\n  Folder: {path}")
    print("  (node_modules, dist, build, .git waghairah chhod diye jayenge)\n")

    try:
        data = code_scanner.scan(path, verbose=True)
    except FileNotFoundError as e:
        print(f"  !! {e}\n")
        return

    st = data["stats"]
    print(f"\n  {st['files_read']} file padhi ({st['seconds']}s)")
    print(f"  {st['elements_total']} element kul  |  {st['new']} naye")
    print(f"  {len(data['routes'])} route mile")

    rows = list(data["elements"].values())
    with_label = [r for r in rows if r.get("label")]
    print(f"  {len(with_label)} element ke saath unka label bhi mila")

    print("\n  Namoona:")
    for r in with_label[:8]:
        print(f"    {r['label'][:28]:<28} -> {r['selectors'][0] if r['selectors'] else '?'}")

    print(f"\n  Yaad rakh li gayi: locators/metadata.json")
    print(f"  Ab koi bhi test in field ko naam se maang sakta hai.\n")


if __name__ == "__main__":
    main()
