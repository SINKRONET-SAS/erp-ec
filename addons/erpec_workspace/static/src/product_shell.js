/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { NavBar } from "@web/webclient/navbar/navbar";

patch(WebClient.prototype, {
    setup() {
        super.setup(...arguments);
        this.title.setParts({ erpec: "ERP EC" });
    },
});

patch(NavBar.prototype, {
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
