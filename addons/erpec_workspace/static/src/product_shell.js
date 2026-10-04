/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { NavBar } from "@web/webclient/navbar/navbar";
import "@web/webclient/user_menu/user_menu_items";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

patch(WebClient.prototype, {
    setup() {
        super.setup(...arguments);
        this.title.setParts({ erpec: "ERP EC" });
        // DI25-06.3: el <html> del cliente web no declara idioma (WCAG 3.1.1); se toma del usuario.
        document.documentElement.setAttribute("lang", (user.lang || user.context.lang || "es").replace("_", "-"));
    },
});

patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);
        // Los accesos del inicio y los menús mantienen la misma área activa.
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", () => {
            const actionId = this.actionService.currentController?.action?.id;
            const menus = this.menuService.getAll().filter((menu) => actionId && Number(menu.actionID) === Number(actionId));
            const selected = menus.find((menu) => menu.appID === this.currentApp?.id) || menus[0];
            if (selected) {
                this.menuService.setCurrentMenu(selected);
            }
        });
    },
    // El menú recibido del servidor ya respeta los permisos del usuario.
    get erpecHomeMenu() {
        return this.menuService.getAll().find((menu) => menu.xmlid === "erpec_operations.operation_menu");
    },
    get erpecSections() {
        const root = this.menuService.getAll().find((menu) => menu.xmlid === "erpec_base.suite_root");
        return root ? this.menuService.getMenuAsTree(root.id).childrenTree : [];
    },
    async erpecOpenHome() {
        if (!this.erpecHomeMenu) {
            throw new Error("Tu perfil no dispone del inicio del ERP. Solicita la revisión del acceso.");
        }
        await this.menuService.selectMenu(this.erpecHomeMenu);
    },
});

// El menú del producto conserva preferencias, atajos y cierre de sesión.
for (const key of ["documentation", "support", "odoo_account"]) {
    registry.category("user_menuitems").remove(key);
}
