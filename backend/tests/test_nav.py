from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
NAV_TS = ROOT / 'frontend' / 'src' / 'features' / 'auth' / 'nav.ts'
APP_TSX = ROOT / 'frontend' / 'src' / 'app' / 'App.tsx'


def _parse_role_list(raw: str) -> list[str]:
    return [part.strip().strip("'\"") for part in raw.split(',') if part.strip()]


def _role_constants(source: str) -> dict[str, list[str]]:
    return {
        name: _parse_role_list(raw)
        for name, raw in re.findall(
            r'export const ([A-Z0-9_]+): UserRole\[\] = \[([^\]]+)\]',
            source,
        )
    }


def _nav_items() -> list[tuple[str, str, list[str]]]:
    source = NAV_TS.read_text(encoding='utf-8')
    constants = _role_constants(source)
    matches = re.findall(
        r"label:\s*'([^']+)',\s*path:\s*'([^']+)',\s*roles:\s*(\[[^\]]+\]|[A-Z0-9_]+)",
        source,
        flags=re.S,
    )
    items = []
    for label, path, roles_raw in matches:
        roles_raw = roles_raw.strip()
        if roles_raw.startswith('['):
            roles = _parse_role_list(roles_raw.strip('[]'))
        else:
            roles = constants[roles_raw]
        items.append((label, path, roles))
    return items


def _paths_for_role(role: str) -> list[str]:
    return [path for _, path, roles in _nav_items() if role in roles]


def test_employee_sees_pos_navigation():
    paths = _paths_for_role('EMPLOYEE')
    assert '/pos' in paths
    assert paths[0] == '/pos' or '/pos' in paths


def test_franchise_owner_does_not_see_pos_navigation():
    assert '/pos' not in _paths_for_role('FRANCHISE_OWNER')


def test_system_admin_does_not_see_pos_navigation():
    assert '/pos' not in _paths_for_role('SYSTEM_ADMIN')


def test_pos_nav_roles_are_employee_only():
    pos = next(item for item in _nav_items() if item[1] == '/pos')
    assert pos[2] == ['EMPLOYEE']


def test_pos_route_is_employee_only():
    source = APP_TSX.read_text(encoding='utf-8')
    assert re.search(
        r"ProtectedRoute roles=\{\['EMPLOYEE'\]\} />\}>\s*<Route path=\"pos\"",
        source,
    )
    assert not re.search(
        r"ProtectedRoute roles=\{[^}]*FRANCHISE_OWNER[^}]*\} />\}>\s*<Route path=\"pos\"",
        source,
    )
    assert not re.search(
        r"ProtectedRoute roles=\{[^}]*SYSTEM_ADMIN[^}]*\} />\}>\s*<Route path=\"pos\"",
        source,
    )


def test_change_password_is_an_authenticated_route():
    source = APP_TSX.read_text(encoding='utf-8')
    assert 'ChangePasswordPage' in source
    assert 'path="change-password"' in source


def test_hidden_modules_are_not_in_navigation():
    labels = {label for label, _, _ in _nav_items()}
    assert 'Inventory' not in labels
    assert 'Recipes' not in labels
    assert 'Franchise Applications' not in labels


def test_admin_does_not_see_employee_management():
    labels = {label for label, path, roles in _nav_items() if 'SYSTEM_ADMIN' in roles}
    assert 'Employees' not in labels
    assert 'User Management' in labels
    paths = _paths_for_role('SYSTEM_ADMIN')
    assert '/employees' not in paths
    assert '/users' in paths


def test_owner_sees_employees_and_menu_pricing():
    paths = _paths_for_role('FRANCHISE_OWNER')
    labels = {label for label, path, roles in _nav_items() if 'FRANCHISE_OWNER' in roles}
    assert '/employees' in paths
    assert '/owner/menu' in paths
    assert '/menu' not in paths
    assert '/bills' in paths
    assert 'Employees' in labels
    assert 'Menu / Pricing' in labels
    assert 'Bills' in labels
    assert 'Change Password' in labels


def test_all_roles_see_bills_navigation():
    assert '/bills' in _paths_for_role('EMPLOYEE')
    assert '/bills' in _paths_for_role('FRANCHISE_OWNER')
    assert '/bills' in _paths_for_role('SYSTEM_ADMIN')


def test_bills_route_is_shared_and_pos_remains_employee_only():
    source = APP_TSX.read_text(encoding='utf-8')
    assert 'path="bills"' in source
    assert 'path="bills/:orderId"' in source
    assert "roles={['SYSTEM_ADMIN', 'FRANCHISE_OWNER', 'EMPLOYEE']}" in source
    assert re.search(
        r"ProtectedRoute roles=\{\['EMPLOYEE'\]\} />\}>\s*<Route path=\"pos\"",
        source,
    )


def test_receipt_reprint_route_is_available_to_all_roles():
    source = APP_TSX.read_text(encoding='utf-8')
    assert 'path="print/receipt/:orderId"' in source
    assert 'ThermalReceiptPage' in source


def test_employee_sees_pos_daily_sales_profile_and_password():
    paths = _paths_for_role('EMPLOYEE')
    labels = {label for label, path, roles in _nav_items() if 'EMPLOYEE' in roles}
    assert paths == ['/pos', '/daily-sales', '/bills', '/profile']
    assert '/' not in paths
    assert '/reports' not in paths
    assert '/menu' not in paths
    assert 'POS' in labels
    assert 'Daily Sales' in labels
    assert 'Bills' in labels
    assert 'My Profile' in labels
    assert 'Change Password' not in labels
    assert 'Dashboard' not in labels
    assert 'Reports' not in labels
    assert 'Menu / Pricing' not in labels
    assert 'Employees' not in labels
    assert 'Inventory' not in labels
    assert 'Recipes' not in labels
    assert 'Franchise Applications' not in labels


def test_admin_sees_bills_gst_and_offers():
    paths = _paths_for_role('SYSTEM_ADMIN')
    assert '/bills' in paths
    assert '/pos' not in paths
    assert '/settings/gst' in paths
    assert '/admin/promotions' in paths
    assert '/settings/offers' not in paths


def test_owner_and_employee_do_not_see_gst_or_offers_settings():
    assert '/settings/gst' not in _paths_for_role('FRANCHISE_OWNER')
    assert '/settings/offers' not in _paths_for_role('FRANCHISE_OWNER')
    assert '/admin/promotions' not in _paths_for_role('FRANCHISE_OWNER')
    assert '/owner/offers' in _paths_for_role('FRANCHISE_OWNER')
    assert '/settings/gst' not in _paths_for_role('EMPLOYEE')
    assert '/settings/offers' not in _paths_for_role('EMPLOYEE')
    assert '/owner/offers' not in _paths_for_role('EMPLOYEE')


def test_admin_sees_dashboard_reports_and_existing_modules():
    paths = _paths_for_role('SYSTEM_ADMIN')
    labels = {label for label, path, roles in _nav_items() if 'SYSTEM_ADMIN' in roles}
    assert '/dashboard' in paths
    assert '/' not in paths
    assert '/franchises' in paths
    assert '/products' in paths
    assert '/users' in paths
    assert '/reports' in paths
    assert '/bills' in paths
    assert '/admin/gallery' in paths
    assert '/pos' not in paths
    assert '/daily-sales' not in paths
    assert 'Dashboard' in labels
    assert 'Franchise Management' in labels
    assert 'Menu / Products' in labels
    assert 'User Management' in labels
    assert 'Reports' in labels
    assert 'Bills' in labels
    assert 'Gallery Management' in labels
    assert 'Daily Sales' not in labels


def test_owner_sees_dashboard_reports_and_existing_modules():
    paths = _paths_for_role('FRANCHISE_OWNER')
    labels = {label for label, path, roles in _nav_items() if 'FRANCHISE_OWNER' in roles}
    assert '/dashboard' in paths
    assert '/' not in paths
    assert '/employees' in paths
    assert '/owner/menu' in paths
    assert '/menu' not in paths
    assert '/reports' in paths
    assert '/bills' in paths
    assert '/gallery' not in paths
    assert '/admin/gallery' not in paths
    assert '/pos' not in paths
    assert '/daily-sales' not in paths
    assert 'Dashboard' in labels
    assert 'Employees' in labels
    assert 'Menu / Pricing' in labels
    assert 'Reports' in labels
    assert 'Bills' in labels
    assert 'Gallery Management' not in labels
    assert 'Daily Sales' not in labels


def test_reports_route_is_admin_and_owner_only():
    source = APP_TSX.read_text(encoding='utf-8')
    assert 'ReportsPage' in source
    assert 'path="reports"' in source
    assert "roles={['SYSTEM_ADMIN', 'FRANCHISE_OWNER']}" in source
    employee_reports = re.search(
        r"ProtectedRoute roles=\{\['EMPLOYEE'\]\} />\}>\s*<Route path=\"reports\"",
        source,
    )
    assert employee_reports is None


def test_daily_sales_route_is_employee_only():
    source = APP_TSX.read_text(encoding='utf-8')
    assert 'DailySalesPage' in source
    assert 'path="daily-sales"' in source
    assert re.search(
        r"ProtectedRoute roles=\{\['EMPLOYEE'\]\} />\}>\s*<Route path=\"pos\"",
        source,
    )
    assert re.search(
        r'<Route path="daily-sales" element=\{<DailySalesPage />\} />',
        source,
    )
    assert not re.search(
        r"ProtectedRoute roles=\{[^}]*FRANCHISE_OWNER[^}]*\} />\}>\s*<Route path=\"daily-sales\"",
        source,
    )
    assert not re.search(
        r"ProtectedRoute roles=\{[^}]*SYSTEM_ADMIN[^}]*\} />\}>\s*<Route path=\"daily-sales\"",
        source,
    )


def test_home_renders_role_dashboards_not_placeholder():
    source = APP_TSX.read_text(encoding='utf-8')
    assert 'path="dashboard"' in source
    assert 'HomePage' in source
    home = (ROOT / 'frontend' / 'src' / 'features' / 'home' / 'HomePage.tsx').read_text(encoding='utf-8')
    assert 'AdminDashboardPage' in home
    assert 'OwnerDashboardPage' in home
    assert "profile?.role === 'EMPLOYEE'" in home
    assert 'Navigate to="/pos"' in home


def test_admin_and_owner_see_change_password_navigation():
    assert '/change-password' in _paths_for_role('SYSTEM_ADMIN')
    assert '/change-password' in _paths_for_role('FRANCHISE_OWNER')
    assert '/change-password' not in _paths_for_role('EMPLOYEE')
    admin_labels = {label for label, path, roles in _nav_items() if 'SYSTEM_ADMIN' in roles}
    owner_labels = {label for label, path, roles in _nav_items() if 'FRANCHISE_OWNER' in roles}
    assert 'Change Password' in admin_labels
    assert 'Change Password' in owner_labels


def test_daily_sales_page_has_single_date_selector():
    source = (ROOT / 'frontend' / 'src' / 'features' / 'reports' / 'DailySalesPage.tsx').read_text(
        encoding='utf-8'
    )
    assert 'type="date"' in source
    assert 'max={today}' in source
    assert 'Last 7 Days' not in source
    assert 'Last 30 Days' not in source
    assert 'No sales on this date' in source


def test_public_routes_are_outside_protected_route():
    source = APP_TSX.read_text(encoding='utf-8')
    public_block = source.split('<Route element={<ProtectedRoute />}>')[0]
    for path in ('index', 'menu', 'about', 'gallery', 'contact'):
        assert f'path="{path}"' in public_block or (path == 'index' and 'PublicHomePage' in public_block)
    assert 'PublicHomePage' in public_block
    assert 'PublicMenuPage' in public_block
    assert 'AboutPage' in public_block
    assert 'PublicGalleryPage' in public_block
    assert 'ContactPage' in public_block
    assert 'PublicLayout' in public_block
    assert '<Route element={<PublicLayout />}>' in public_block
    assert 'Navigate to="/login"' not in public_block


def test_public_menu_is_not_owner_menu():
    source = APP_TSX.read_text(encoding='utf-8')
    assert 'path="owner/menu"' in source
    assert 'OwnerMenuPage' in source
    assert 'PublicMenuPage' in source
    nav = NAV_TS.read_text(encoding='utf-8')
    assert "path: '/owner/menu'" in nav
    assert "path: '/menu',\n    roles: ['FRANCHISE_OWNER']" not in nav


def test_staff_landing_paths():
    source = NAV_TS.read_text(encoding='utf-8')
    assert "if (role === 'EMPLOYEE') return '/pos'" in source
    assert "return '/dashboard'" in source
    login = (ROOT / 'frontend' / 'src' / 'features' / 'auth' / 'LoginPage.tsx').read_text(
        encoding='utf-8'
    )
    assert 'staffLandingPath' in login
    assert 'Navigate to="/" replace' not in login
    assert 'Sign in to your account' not in login
    assert 'Staff Login' in login
    assert 'Enter email or user ID' in login
    assert 'Email/User ID' in login


def test_unauthenticated_staff_routes_still_use_protected_route():
    source = APP_TSX.read_text(encoding='utf-8')
    protected = source.split('<Route element={<ProtectedRoute />}>', 1)[1]
    for path in (
        'dashboard',
        'pos',
        'daily-sales',
        'bills',
        'products',
        'franchises',
        'owner/menu',
        'admin/gallery',
        'reports',
        'audit',
    ):
        assert f'path="{path}"' in protected


def test_admin_and_owner_see_audit_employee_does_not():
    assert '/audit' in _paths_for_role('SYSTEM_ADMIN')
    assert '/audit' in _paths_for_role('FRANCHISE_OWNER')
    assert '/audit' not in _paths_for_role('EMPLOYEE')
    employee_labels = {label for label, path, roles in _nav_items() if 'EMPLOYEE' in roles}
    assert 'Audit' not in employee_labels
    source = APP_TSX.read_text(encoding='utf-8')
    assert 'AuditsPage' in source
    assert 'CreateAuditPage' in source
    assert 'AuditDetailPage' in source
    assert 'Quality audits coming in a later milestone' not in source
    assert "roles={['SYSTEM_ADMIN', 'FRANCHISE_OWNER']}" in source
    assert not re.search(
        r"ProtectedRoute roles=\{\['EMPLOYEE'\]\} />\}>\s*<Route path=\"audit\"",
        source,
    )
    nav = NAV_TS.read_text(encoding='utf-8')
    assert "export const AUDIT_ACCESS_ROLES: UserRole[] = ['SYSTEM_ADMIN', 'FRANCHISE_OWNER']" in nav
    assert 'canAccessAudit' in nav
    assert 'franchiseOwnerAuditEnabled' in nav
    assert 'AuditProtectedRoute' in source
    audit_item = next(item for item in _nav_items() if item[1] == '/audit')
    assert audit_item[2] == ['SYSTEM_ADMIN', 'FRANCHISE_OWNER']


def test_audit_option_is_nav_not_franchise_management_action():
    franchises = (ROOT / 'frontend' / 'src' / 'features' / 'franchises' / 'FranchisesPage.tsx').read_text(
        encoding='utf-8'
    )
    detail = (ROOT / 'frontend' / 'src' / 'features' / 'franchises' / 'FranchiseDetailPage.tsx').read_text(
        encoding='utf-8'
    )
    settings_copy = (
        ROOT / 'frontend' / 'src' / 'features' / 'franchises' / 'franchiseAuditSetting.ts'
    ).read_text(encoding='utf-8')
    settings_ui = (
        ROOT / 'frontend' / 'src' / 'features' / 'franchises' / 'FranchiseAuditSettings.tsx'
    ).read_text(encoding='utf-8')
    assert 'FranchiseAuditSettings' in franchises
    assert "to={`/audit" not in franchises
    assert 'path="/audit"' not in franchises
    assert 'Audit' not in detail
    assert 'Allow Franchise Owners to access Audit' in settings_copy
    assert 'FRANCHISE_AUDIT_SETTING_COPY.label' in settings_ui
    audit_item = next(item for item in _nav_items() if item[0] == 'Audit')
    assert audit_item[1] == '/audit'


def test_receipt_route_remains_outside_appshell():
    source = APP_TSX.read_text(encoding='utf-8')
    before_shell = source.split('<Route element={<AppShell />}>')[0]
    assert 'path="print/receipt/:orderId"' in before_shell
    receipt = (ROOT / 'frontend' / 'src' / 'features' / 'pos' / 'ThermalReceiptPage.tsx').read_text(
        encoding='utf-8'
    )
    assert 'thermal-receipt.css' in receipt


def test_owner_and_employee_do_not_manage_gallery():
    assert '/admin/gallery' not in _paths_for_role('FRANCHISE_OWNER')
    assert '/admin/gallery' not in _paths_for_role('EMPLOYEE')
    assert '/admin/gallery' in _paths_for_role('SYSTEM_ADMIN')


def test_public_home_uses_official_brand_image():
    hero = (ROOT / 'frontend' / 'src' / 'features' / 'public' / 'HeroArt.tsx').read_text(
        encoding='utf-8'
    )
    home = (ROOT / 'frontend' / 'src' / 'features' / 'public' / 'HomePage.tsx').read_text(
        encoding='utf-8'
    )
    layout = (ROOT / 'frontend' / 'src' / 'components' / 'layout' / 'PublicLayout.tsx').read_text(
        encoding='utf-8'
    )
    brand_ts = (ROOT / 'frontend' / 'src' / 'components' / 'branding' / 'brand.ts').read_text(
        encoding='utf-8'
    )
    logo = ROOT / 'frontend' / 'public' / 'realstick-logo.jpeg'
    assert "from '../../components/branding/RealStickLogo'" in hero
    assert '<RealStickLogo' in hero
    assert 'BrandHero' in home
    assert '<RealStickLogo' in layout
    assert "REALSTICK_LOGO_SRC = '/realstick-logo.jpeg'" in brand_ts
    assert logo.exists()
    assert logo.stat().st_size > 0
    assert logo.read_bytes()[:3] == b'\xff\xd8\xff'


def test_view_gallery_button_has_readable_contrast():
    home = (ROOT / 'frontend' / 'src' / 'features' / 'public' / 'HomePage.tsx').read_text(
        encoding='utf-8'
    )
    ui = (ROOT / 'frontend' / 'src' / 'components' / 'ui' / 'index.tsx').read_text(encoding='utf-8')
    assert 'variant="onDark"' in home
    assert 'View Gallery' in home
    assert 'bg-white text-[#0D4F2E]' in ui


def test_pos_page_still_uses_frozen_checkout():
    source = (ROOT / 'frontend' / 'src' / 'features' / 'pos' / 'PosPage.tsx').read_text(
        encoding='utf-8'
    )
    assert 'completePosOrder' in source
    assert 'previewTotals' in source
    assert 'thermal-receipt.css' not in source
    assert 'gstRate' in source

