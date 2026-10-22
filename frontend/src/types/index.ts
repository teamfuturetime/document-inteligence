export type User={id:string;email:string;username:string;created_at:string}
export type Document={id:string;filename:string;content_type:string;file_size:number;status:string;ocr_text?:string;created_at:string;updated_at:string;expires_at?:string}
export type Extraction={id:string;document_id:string;document_type:string;data:Record<string,unknown>;confidence:number;classification_metadata?:{confidence_type?:string;matched_rules?:string[];needs_review?:boolean};status:string;created_at:string;updated_at:string;confirmed_at?:string}
export type DocumentList={items:Document[];total:number;page:number;page_size:number}
export type Dashboard={total:number;processed:number;awaiting_review:number;confirmed:number;recent:Document[]}
