import{act,cleanup,fireEvent,render,screen,waitFor}from'@testing-library/react'
import{afterEach,beforeEach,describe,expect,it,vi}from'vitest'
import'@testing-library/jest-dom/vitest'
import{Link,createMemoryRouter,RouterProvider,Route,Routes}from'react-router-dom'
import DocumentDetailPage from'./DocumentDetailPage'
import type{Document,Extraction}from'../types'

const mocks=vi.hoisted(()=>({get:vi.fn(),extraction:vi.fn(),save:vi.fn(),saveOcr:vi.fn(),confirm:vi.fn(),reopen:vi.fn(),process:vi.fn()}))
vi.mock('../api/client',()=>{
 class ApiError extends Error{constructor(public status:number,message:string){super(message)}}
 return{ApiError,api:{...mocks,preview:(id:string)=>`/preview/${id}`,export:(id:string)=>`/export/${id}`}}
})

const document:Document={id:'doc-1',filename:'mau.pdf',content_type:'application/pdf',file_size:1024,status:'processed',ocr_revision:0,ocr_text:'RAW',ocr_text_raw:'RAW',ocr_text_cleaned:'Sạch',ocr_is_corrected:false,created_at:'2026-01-01',updated_at:'2026-01-01'}
const extraction:Extraction={id:'ext-1',document_id:'doc-1',document_type:'unknown',ai_document_type:'unknown',reviewed_document_type:null,data:{'Họ tên':'Nguyễn Văn A'},confidence:0,status:'pending_review',created_at:'2026-01-01',updated_at:'2026-01-01'}
function view(){
 const router=createMemoryRouter([{path:'*',element:<><Link to="/documents/doc-2">Tài liệu tiếp theo</Link><Routes><Route path="/documents/:id" element={<DocumentDetailPage/>}/><Route path="/documents" element={<div>Danh sách</div>}/></Routes></>}],{initialEntries:['/documents/doc-0','/documents/doc-1'],initialIndex:1})
 return {...render(<RouterProvider router={router}/>),router}
}

describe('DocumentDetailPage review',()=>{
 beforeEach(()=>{sessionStorage.clear();Object.values(mocks).forEach(mock=>mock.mockReset());mocks.get.mockResolvedValue({...document});mocks.extraction.mockResolvedValue({...extraction});mocks.save.mockResolvedValue(extraction);mocks.confirm.mockResolvedValue({...extraction,status:'confirmed'});mocks.reopen.mockResolvedValue(extraction);vi.spyOn(window,'confirm').mockReturnValue(true)})
 afterEach(()=>{cleanup();vi.restoreAllMocks()})

 it('vào chế độ sửa, thêm và xóa trường, sau đó lưu',async()=>{
  view();fireEvent.click(await screen.findByRole('button',{name:/Chỉnh sửa dữ liệu/}));fireEvent.click(screen.getByRole('button',{name:/Thêm trường/}))
  const names=screen.getAllByLabelText(/Tên trường/);const values=screen.getAllByLabelText(/Giá trị trường/)
  fireEvent.change(names[1],{target:{value:'Ghi chú'}});fireEvent.change(values[1],{target:{value:'Đã đối chiếu'}})
  fireEvent.click(screen.getByRole('button',{name:'Xóa trường 1'}));expect(screen.queryByDisplayValue('Nguyễn Văn A')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:/Lưu thay đổi/}))
  await waitFor(()=>expect(mocks.save).toHaveBeenCalledWith('doc-1',{'Ghi chú':'Đã đối chiếu'},'unknown'))
 })

 it('cho phép tạo trường khi classification unknown và chưa có extraction',async()=>{
  const{ApiError}=await import('../api/client');mocks.extraction.mockRejectedValue(new ApiError(404,'Không có extraction'))
  view();fireEvent.click(await screen.findByRole('button',{name:/Chỉnh sửa dữ liệu/}));fireEvent.click(screen.getByRole('button',{name:/Thêm trường/}));fireEvent.change(screen.getByLabelText('Tên trường 1'),{target:{value:'Số hồ sơ'}});fireEvent.change(screen.getByLabelText('Giá trị trường 1'),{target:{value:'HS-01'}});fireEvent.click(screen.getByRole('button',{name:/Lưu thay đổi/}))
  await waitFor(()=>expect(mocks.save).toHaveBeenCalledWith('doc-1',{'Số hồ sơ':'HS-01'},'unknown'))
 })

 it('hủy giữ nguyên dữ liệu và hiển thị lỗi backend',async()=>{
  mocks.save.mockRejectedValue(new Error('Không thể kết nối máy chủ'));view();fireEvent.click(await screen.findByRole('button',{name:/Chỉnh sửa dữ liệu/}));fireEvent.change(screen.getByLabelText('Giá trị trường 1'),{target:{value:'Đã đổi'}});fireEvent.click(screen.getByRole('button',{name:/Hủy/}));expect(screen.getByText('Nguyễn Văn A')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:/Chỉnh sửa dữ liệu/}));fireEvent.change(screen.getByLabelText('Giá trị trường 1'),{target:{value:'Đã đổi'}});fireEvent.click(screen.getByRole('button',{name:/Lưu thay đổi/}));expect(await screen.findByRole('alert')).toHaveTextContent('Không thể kết nối máy chủ')
 })

 it('hiển thị chỉ đọc sau xác nhận và cho phép mở lại rõ ràng',async()=>{
  mocks.get.mockResolvedValue({...document,status:'confirmed'});mocks.extraction.mockResolvedValue({...extraction,status:'confirmed',confirmed_at:'2026-01-02'});view();expect(await screen.findByText(/Kết quả đã được xác nhận/)).toBeInTheDocument();expect(screen.queryByRole('button',{name:/Chỉnh sửa dữ liệu/})).not.toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:/Mở lại rà soát/}));await waitFor(()=>expect(mocks.reopen).toHaveBeenCalledWith('doc-1'))
 })
})

function deferred<T>(){
 let resolve!:(value:T)=>void
 const promise=new Promise<T>(yes=>{resolve=yes})
 return{promise,resolve}
}
const advance=(ms:number)=>act(async()=>{await vi.advanceTimersByTimeAsync(ms)})
const flush=()=>act(async()=>{await Promise.resolve()})
const typeOCR=(text:string)=>fireEvent.change(screen.getByRole('textbox',{name:'Nội dung OCR đã hiệu chỉnh'}),{target:{value:text}})

const clickSave=()=>fireEvent.click(screen.getByRole('button',{name:'Lưu OCR'}))

describe('DocumentDetailPage explicit OCR save integration',()=>{
 beforeEach(()=>{
  vi.useFakeTimers();sessionStorage.clear();Object.values(mocks).forEach(mock=>mock.mockReset())
  mocks.get.mockImplementation(async(id:string)=>({...document,id,filename:id+'.pdf'}))
  mocks.extraction.mockResolvedValue({...extraction})
  mocks.saveOcr.mockImplementation(async(id:string,text:string,revision:number)=>({...document,id,filename:id+'.pdf',status:'reviewed',ocr_text_cleaned:text,ocr_is_corrected:true,ocr_revision:revision+1}))
  vi.spyOn(window,'confirm').mockReturnValue(false)
 })
 afterEach(()=>{cleanup();vi.useRealTimers();vi.restoreAllMocks()})

 it('TC01/03 requires explicit save, blocks confirm until acknowledgement and preserves revision',async()=>{
  const request=deferred<Document>();mocks.saveOcr.mockReturnValueOnce(request.promise)
  view();await flush()
  fireEvent.click(screen.getByRole('button',{name:/Chỉnh sửa văn bản OCR/}));typeOCR('Bản đã kiểm tra')
  expect(screen.getByRole('button',{name:/Xác nhận kết quả/})).toBeDisabled()
  await advance(10000);expect(mocks.saveOcr).not.toHaveBeenCalled()
  clickSave();expect(mocks.saveOcr).toHaveBeenCalledWith('doc-1','Bản đã kiểm tra',0)
  expect(screen.getByRole('button',{name:/Xác nhận kết quả/})).toBeDisabled()
  await act(async()=>request.resolve({...document,status:'reviewed',ocr_revision:1,ocr_text_cleaned:'Bản đã kiểm tra'}))
  expect(screen.getByRole('button',{name:/Xác nhận kết quả/})).toBeEnabled()
  typeOCR('Bản tiếp theo');await advance(10000);expect(mocks.saveOcr).toHaveBeenCalledTimes(1)
  clickSave();await flush()
  expect(mocks.saveOcr).toHaveBeenLastCalledWith('doc-1','Bản tiếp theo',1)
 })

 it('TC02 reloads backend text after discarding an unsaved local edit',async()=>{
  const first=view();await flush();fireEvent.click(screen.getByRole('button',{name:/Chỉnh sửa văn bản OCR/}));typeOCR('Bản chưa gửi')
  const beforeReload=new Event('beforeunload',{cancelable:true});window.dispatchEvent(beforeReload)
  expect(beforeReload.defaultPrevented).toBe(true)
  first.unmount();view();await flush();await advance(10000)
  expect(screen.getByText('Sạch')).toBeInTheDocument()
  expect(mocks.saveOcr).not.toHaveBeenCalled()
 })

 it('TC05/08 keeps a conflicted draft and can cancel navigation to the list',async()=>{
  const{ApiError}=await import('../api/client');mocks.saveOcr.mockRejectedValue(new ApiError(409,'Conflict'))
  view();await flush();fireEvent.click(screen.getByRole('button',{name:/Chỉnh sửa văn bản OCR/}));typeOCR('Nháp xung đột');clickSave();await flush()
  expect(screen.getByRole('alert')).toHaveTextContent(/xung đột/i)
  fireEvent.click(screen.getByRole('link',{name:'Quay lại'}));await flush()
  expect(window.confirm).toHaveBeenCalledTimes(1)
  expect(screen.getByRole('textbox')).toHaveValue('Nháp xung đột')
  expect(screen.queryByText('Danh sách')).not.toBeInTheDocument()
  await advance(10000);expect(mocks.saveOcr).toHaveBeenCalledTimes(1)
 })

 it('TC08 guards other document links and discards without saving only after confirmation',async()=>{
  view();await flush();fireEvent.click(screen.getByRole('button',{name:/Chỉnh sửa văn bản OCR/}));typeOCR('Bản chưa lưu')
  fireEvent.click(screen.getByRole('link',{name:'Tài liệu tiếp theo'}));await flush()
  expect(window.confirm).toHaveBeenCalledTimes(1)
  expect(screen.getByRole('heading',{name:'doc-1.pdf'})).toBeInTheDocument()
  expect(screen.getByRole('textbox')).toHaveValue('Bản chưa lưu')
  vi.mocked(window.confirm).mockReturnValue(true)
  fireEvent.click(screen.getByRole('link',{name:'Tài liệu tiếp theo'}));await flush();await advance(10000)
  expect(screen.getByRole('heading',{name:'doc-2.pdf'})).toBeInTheDocument()
  expect(mocks.saveOcr).not.toHaveBeenCalled()
 })

 it('TC08 guards browser Back navigation',async()=>{
  const{router}=view();await flush();fireEvent.click(screen.getByRole('button',{name:/Chỉnh sửa văn bản OCR/}));typeOCR('Giữ lại')
  await act(async()=>{await router.navigate(-1)})
  expect(window.confirm).toHaveBeenCalledTimes(1)
  expect(screen.getByRole('heading',{name:'doc-1.pdf'})).toBeInTheDocument()
  expect(mocks.saveOcr).not.toHaveBeenCalled()
 })

 it('ignores an earlier manually requested save after leaving for another document',async()=>{
  const old=deferred<Document>();mocks.saveOcr.mockReturnValueOnce(old.promise)
  view();await flush();fireEvent.click(screen.getByRole('button',{name:/Chỉnh sửa văn bản OCR/}));typeOCR('Nháp tài liệu một');clickSave()
  vi.mocked(window.confirm).mockReturnValue(true)
  fireEvent.click(screen.getByRole('link',{name:'Tài liệu tiếp theo'}));await flush()
  fireEvent.click(screen.getByRole('button',{name:/Chỉnh sửa văn bản OCR/}));typeOCR('Nháp tài liệu hai');clickSave();await flush()
  await act(async()=>old.resolve({...document,status:'reviewed',ocr_revision:1,ocr_text_cleaned:'Nháp tài liệu một'}))
  expect(screen.getByRole('heading',{name:'doc-2.pdf'})).toBeInTheDocument()
  expect(screen.getByRole('textbox')).toHaveValue('Nháp tài liệu hai')
 })

 it('TC10 confirmed documents expose no OCR edit action',async()=>{
  mocks.get.mockResolvedValue({...document,status:'confirmed'})
  view();await flush();await advance(10000)
  expect(screen.queryByRole('button',{name:/Chỉnh sửa văn bản OCR/})).not.toBeInTheDocument()
  expect(mocks.saveOcr).not.toHaveBeenCalled()
 })

 it('TC10 exports, confirms and reopens after a successful explicit OCR save',async()=>{
  view();await flush();fireEvent.click(screen.getByRole('button',{name:/Chỉnh sửa văn bản OCR/}));typeOCR('Bản đã duyệt');clickSave();await flush()
  expect(screen.getByRole('link',{name:'Xuất JSON'})).toHaveAttribute('href','/export/doc-1')
  mocks.get.mockResolvedValue({...document,status:'confirmed',ocr_revision:1,ocr_text_cleaned:'Bản đã duyệt'})
  mocks.confirm.mockResolvedValue({...extraction,status:'confirmed'})
  fireEvent.click(screen.getByRole('button',{name:/Xác nhận kết quả/}));await flush()
  expect(mocks.confirm).toHaveBeenCalledWith('doc-1')
  expect(screen.getByText(/Kết quả đã được xác nhận/)).toBeInTheDocument()
  mocks.get.mockResolvedValue({...document,status:'reviewed',ocr_revision:1,ocr_text_cleaned:'Bản đã duyệt'})
  mocks.reopen.mockResolvedValue(extraction)
  fireEvent.click(screen.getByRole('button',{name:/Mở lại rà soát/}));await flush()
  expect(mocks.reopen).toHaveBeenCalledWith('doc-1')
  expect(screen.getByRole('textbox')).toBeEnabled()
  expect(mocks.saveOcr).toHaveBeenCalledTimes(1)
 })

 it('TC10 saving extraction does not implicitly save a pending OCR draft',async()=>{
  mocks.save.mockResolvedValue(extraction)
  view();await flush();fireEvent.click(screen.getByRole('button',{name:/Chỉnh sửa văn bản OCR/}));typeOCR('Chưa được lưu')
  fireEvent.click(screen.getByRole('button',{name:/Chỉnh sửa dữ liệu/}))
  fireEvent.change(screen.getByLabelText('Giá trị trường 1'),{target:{value:'Đã đối chiếu'}})
  fireEvent.click(screen.getByRole('button',{name:/Lưu thay đổi/}));await flush();await advance(10000)
  expect(mocks.save).toHaveBeenCalledWith('doc-1',{'Họ tên':'Đã đối chiếu'},'unknown')
  expect(screen.getByRole('textbox')).toHaveValue('Chưa được lưu')
  expect(mocks.saveOcr).not.toHaveBeenCalled()
  expect(screen.getByRole('button',{name:/Xác nhận kết quả/})).toBeDisabled()
 })

 it('preserves a confirmed reload when a manual save response with the same revision arrives late',async()=>{
  const old=deferred<Document>();mocks.saveOcr.mockReturnValueOnce(old.promise)
  view();await flush();fireEvent.click(screen.getByRole('button',{name:/Chỉnh sửa văn bản OCR/}));typeOCR('Đã lưu tại server');clickSave()
  fireEvent.click(screen.getByRole('button',{name:/Chỉnh sửa dữ liệu/}))
  fireEvent.change(screen.getByLabelText('Giá trị trường 1'),{target:{value:'Đã đối chiếu'}})
  mocks.save.mockResolvedValue(extraction)
  mocks.get.mockResolvedValue({...document,filename:'doc-1.pdf',status:'confirmed',ocr_revision:1,ocr_text_cleaned:'Đã lưu tại server'})
  mocks.extraction.mockResolvedValue({...extraction,status:'confirmed'})
  fireEvent.click(screen.getByRole('button',{name:/Lưu thay đổi/}));await flush()
  await act(async()=>old.resolve({...document,filename:'doc-1.pdf',status:'reviewed',ocr_revision:1,ocr_text_cleaned:'Đã lưu tại server'}))
  expect(screen.getByText(/Kết quả đã được xác nhận/)).toBeInTheDocument()
  expect(screen.getByRole('textbox')).toBeDisabled()
 })

 it('prevents OCR edits while confirmation is pending',async()=>{
  const confirm=deferred<Extraction>();mocks.confirm.mockReturnValue(confirm.promise)
  view();await flush();fireEvent.click(screen.getByRole('button',{name:/Chỉnh sửa văn bản OCR/}))
  fireEvent.click(screen.getByRole('button',{name:/Xác nhận kết quả/}))
  expect(screen.getByRole('textbox')).toBeDisabled()
  await advance(10000);expect(mocks.saveOcr).not.toHaveBeenCalled()
  mocks.get.mockResolvedValue({...document,status:'confirmed'})
  await act(async()=>confirm.resolve({...extraction,status:'confirmed'}))
  expect(screen.getByText(/Kết quả đã được xác nhận/)).toBeInTheDocument()
 })
})
