export const statement=(env,sql,...args)=>env.DB.prepare(sql).bind(...args);
export const first=(env,sql,...args)=>statement(env,sql,...args).first();
export const rows=async(env,sql,...args)=>(await statement(env,sql,...args).all()).results;
export const run=(env,sql,...args)=>statement(env,sql,...args).run();
