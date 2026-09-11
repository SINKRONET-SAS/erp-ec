"use strict";
// Alta administrativa local autorizada. No envía mensajes ni acepta contratos.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { createRequire } = require('node:module');
const backend = 'C:/proyectos web/sinkroniq-mobile/backend';
const localRequire = createRequire(path.join(backend, 'package.json'));
const envValues = localRequire('dotenv').parse(fs.readFileSync(path.join(backend,'.env')));
const target = new URL(envValues.DATABASE_URL);
if (!['127.0.0.1','localhost'].includes(target.hostname) || target.pathname !== '/sinkronet_fact') {
  throw new Error('Solo se permite la base local sinkronet_fact');
}
process.env.DATABASE_URL=envValues.DATABASE_URL;
const { prisma } = require(path.join(backend,'src/utils/prisma'));
const { ensureOwnerCommercialStructure } = require(path.join(backend,'src/services/workspace/commercialStructureService'));
const bcrypt = localRequire('bcrypt');
const state='C:/proyectos web/ERP/_EC/.cache/windows';
const secretFile=path.join(state,'facturador-test-issuer.json');
const email='info@sinkronet.com.ec';
const ruc='1793235327001';
const correlationId=crypto.randomUUID();
async function main() {
 const existing = await prisma.user.findMany({where:{OR:[{email},{ruc}]},select:{id:true,email:true,ruc:true}});
 if (existing.length > 1 || (existing.length && (existing[0].email!==email || existing[0].ruc!==ruc))) {
   throw new Error('El correo y el RUC no identifican inequívocamente al mismo emisor');
 }
 let privateData=fs.existsSync(secretFile) ? JSON.parse(fs.readFileSync(secretFile,'utf8')) : {email,password:crypto.randomBytes(24).toString('base64url')};
 if (!fs.existsSync(secretFile)) fs.writeFileSync(secretFile,JSON.stringify(privateData),{encoding:'utf8',flag:'wx'});
 let user;
 if (existing.length) {
   user=await prisma.user.update({where:{id:existing[0].id},data:{ambiente:'1'}});
 } else {
   const password=await bcrypt.hash(privateData.password,12);
   user=await prisma.$transaction(async tx=>{
     const created=await tx.user.create({data:{email,password,nombre:'SINKRONET S.A.S.',razonSocial:'SINKRONET S.A.S.',nombreComercial:'SINKRONET',ruc,role:'OWNER',ambiente:'1',activo:true,accountStatus:'ACTIVE',establecimiento:'',puntoEmision:'',planActivo:'FREE',isSubscriptionActive:false,isProviderBillingIssuer:false}});
     await tx.user.update({where:{id:created.id},data:{empresaId:created.id}});
     await tx.secuencial.create({data:{userId:created.id,value:0}});
     return created;
   });
 }
 const structure=await ensureOwnerCommercialStructure(prisma,user.id);
 const empresa=await prisma.empresa.findUnique({where:{ownerUserId:user.id}});
 if (!empresa || empresa.ambiente!=='1') throw new Error('La empresa no quedó en ambiente de pruebas');
 const keys=await prisma.apiKey.findMany({where:{empresaId:empresa.id,activa:true},select:{id:true,ambiente:true}});
 if (keys.some(key=>key.ambiente!=='PRUEBAS')) throw new Error('Existen credenciales activas fuera de pruebas; se requiere revisar la integración');
 const result={correlationId,created:!existing.length,userId:user.id,empresaId:empresa.id,workspaceId:empresa.workspaceId,email,ruc,ambienteUsuario:'1',ambienteEmpresa:empresa.ambiente,activeApiKeys:keys.length,productionEmission:false,emailsSent:false,certificateConfigured:false,emissionPointConfigured:false};
 fs.writeFileSync(path.join(state,'facturador-test-issuer-result.json'),JSON.stringify(result,null,2)+'\n','utf8');
 console.log(JSON.stringify(result));
}
main().catch(error=>{console.error(JSON.stringify({code:'ERPEC_TEST_ISSUER_FAILED',statusCode:500,correlationId,errorType:error.name,message:'No se pudo completar el alta local; revisar el estado antes de reintentar.'}));process.exitCode=1;}).finally(()=>prisma.$disconnect());
