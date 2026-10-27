import{cleanup,fireEvent,render,screen,waitFor}from'@testing-library/react'
import{afterEach,beforeEach,describe,expect,it,vi}from'vitest'
import'@testing-library/jest-dom/vitest'
import{MemoryRouter,Route,Routes}from'react-router-dom'
import DocumentDetailPage from'./DocumentDetailPage'
import type{Document,Extraction}from'../types'

const mocks=vi.hoisted(()=>({get:vi.fn(),extraction:vi.fn(),save:vi.fn(),saveOcr:vi.fn(),confirm:vi.fn(),reopen:vi.fn(),process:vi.fn()}))
vi.mock('../api/client',()=>{
 class ApiError extends Error{constructor(public status:number,message:string){super(message)}}
 return{ApiError,api:{...mocks,preview:(id:string)=>`/preview/${id}`,export:(id:string)=>`/export/${id}`}}
})

const document:Document={id:'doc-1',filename:'mau.pdf',content_type:'application/pdf',file_size:1024,status:'processed',ocr_text:'RAW',ocr_text_raw:'RAW',ocr_text_cleaned:'Sạch',ocr_is_corrected:false,created_at:'2026-01-01',updated_at:'2026-01-01'}
const extraction:Extraction={id:'ext-1',document_id:'doc-1',document_type:'unknown',ai_document_type:'unknown',reviewed_document_type:null,data:{'Họ tên':'Nguyễn Văn A'},confidence:0,status:'pending_review',created_at:'2026-01-01',updated_at:'2026-01-01'}
function view(){return render(<MemoryRouter initialEntries={['/documents/doc-1']}><Routes><Route path="/documents/:id" element={<DocumentDetailPage/>}/><Route path="/documents" element={<div>Danh sách</div>}/></Routes></MemoryRouter>)}

describe('DocumentDetailPage review',()=>{
 beforeEach(()=>{Object.values(mocks).forEach(mock=>mock.mockReset());mocks.get.mockResolvedValue({...document});mocks.extraction.mockResolvedValue({...extraction});mocks.save.mockResolvedValue(extraction);mocks.confirm.mockResolvedValue({...extraction,status:'confirmed'});mocks.reopen.mockResolvedValue(extraction);vi.spyOn(window,'confirm').mockReturnValue(true)})
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
