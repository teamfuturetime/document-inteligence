import{cleanup,fireEvent,render,screen,waitFor}from'@testing-library/react'
import{afterEach,beforeEach,describe,expect,it,vi}from'vitest'
import'@testing-library/jest-dom/vitest'
import OCRTextCard from'./OCRTextCard'
import type{OCRPage}from'../types'

const pages:OCRPage[]=[{page_number:1,width:1200,height:1600,blocks:[{type:'key_value',text:'MST: 0101234567',key:'MST',value:'0101234567',confidence:.42,bbox:[10,20,300,40],needs_review:true,lines:[]}]}]

describe('OCRTextCard',()=>{
  const writeText=vi.fn().mockResolvedValue(undefined)
  beforeEach(()=>{writeText.mockClear();Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText}})})
  afterEach(cleanup)

  it('mặc định hiển thị bản dễ đọc và có đủ ba chế độ',()=>{
    render(<OCRTextCard cleanedText="Nội dung dễ đọc" rawText={'NỘI  DUNG\n||||'} pages={pages}/>)
    expect(screen.getByText('Nội dung dễ đọc')).toBeInTheDocument()
    expect(screen.getByRole('tab',{name:'Văn bản dễ đọc'})).toHaveAttribute('aria-selected','true')
    expect(screen.getByRole('tab',{name:'OCR gốc'})).toBeInTheDocument()
    expect(screen.getByRole('tab',{name:'Cấu trúc tài liệu'})).toBeInTheDocument()
  })

  it('hiển thị nguyên văn raw OCR ở chế độ OCR gốc',()=>{
    const{container}=render(<OCRTextCard cleanedText="Sạch" rawText={'NỘI  DUNG\n||||'}/>)
    fireEvent.click(screen.getByRole('tab',{name:'OCR gốc'}))
    expect(container.querySelector('pre')?.textContent).toBe('NỘI  DUNG\n||||')
  })

  it('fallback về raw và hiển thị empty state',()=>{
    const{rerender}=render(<OCRTextCard cleanedText={null} rawText="Nội dung OCR gốc"/>)
    expect(screen.getByText('Nội dung OCR gốc')).toBeInTheDocument()
    rerender(<OCRTextCard cleanedText=" " rawText={null}/>)
    expect(screen.getByText('Chưa có văn bản OCR')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Sao chép'})).toBeDisabled()
  })

  it('hiển thị cấu trúc và confidence OCR thật',()=>{
    render(<OCRTextCard cleanedText="MST: 0101234567" rawText="MST: 0101234567" pages={pages}/>)
    fireEvent.click(screen.getByRole('tab',{name:'Cấu trúc tài liệu'}))
    expect(screen.getByText('Trang 1')).toBeInTheDocument()
    expect(screen.getByText('OCR 42% · cần kiểm tra')).toBeInTheDocument()
    expect(screen.getByText('0101234567')).toBeInTheDocument()
  })

  it('không tạo cấu trúc giả khi backend chưa cung cấp',()=>{
    render(<OCRTextCard cleanedText="Văn bản" rawText="Văn bản" pages={[]}/>)
    fireEvent.click(screen.getByRole('tab',{name:'Cấu trúc tài liệu'}))
    expect(screen.getByText('Chưa có dữ liệu cấu trúc')).toBeInTheDocument()
  })

  it('sao chép nội dung của chế độ đang chọn',async()=>{
    render(<OCRTextCard cleanedText="Nội dung sạch" rawText="Nội dung thô"/>)
    fireEvent.click(screen.getByRole('tab',{name:'OCR gốc'}))
    fireEvent.click(screen.getByRole('button',{name:'Sao chép'}))
    await waitFor(()=>expect(writeText).toHaveBeenCalledWith('Nội dung thô'))
    expect(screen.getByRole('button',{name:'Đã sao chép'})).toBeInTheDocument()
  })

  it('chỉnh sửa, lưu và hiển thị lỗi backend',async()=>{
    const onSave=vi.fn().mockRejectedValueOnce(new Error('Máy chủ từ chối')).mockResolvedValue(undefined)
    render(<OCRTextCard cleanedText="Nội dung cũ" rawText="OCR GỐC" onSave={onSave}/>)
    fireEvent.click(screen.getByRole('button',{name:/Chỉnh sửa văn bản OCR/}))
    fireEvent.change(screen.getByRole('textbox',{name:'Nội dung OCR đã hiệu chỉnh'}),{target:{value:'Nội dung tiếng Việt\nđã sửa'}})
    fireEvent.click(screen.getByRole('button',{name:/Lưu OCR/}))
    expect(await screen.findByRole('alert')).toHaveTextContent('Máy chủ từ chối')
    fireEvent.click(screen.getByRole('button',{name:/Lưu OCR/}))
    await waitFor(()=>expect(onSave).toHaveBeenLastCalledWith('Nội dung tiếng Việt\nđã sửa'))
    expect(await screen.findByRole('status')).toHaveTextContent('Đã lưu văn bản OCR chỉnh sửa')
  })

  it('hủy chỉnh sửa và khóa editor khi đã xác nhận',()=>{
    const confirm=vi.spyOn(window,'confirm').mockReturnValue(true)
    const{rerender}=render(<OCRTextCard cleanedText="Nội dung cũ" rawText="OCR GỐC" onSave={vi.fn()}/>)
    fireEvent.click(screen.getByRole('button',{name:/Chỉnh sửa văn bản OCR/}))
    fireEvent.change(screen.getByRole('textbox'),{target:{value:'Chưa lưu'}})
    fireEvent.click(screen.getByRole('button',{name:/Hủy/}))
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    expect(confirm).toHaveBeenCalled()
    rerender(<OCRTextCard cleanedText="Đã chốt" rawText="OCR GỐC" readOnly onSave={vi.fn()} corrected/>)
    expect(screen.queryByRole('button',{name:/Chỉnh sửa văn bản OCR/})).not.toBeInTheDocument()
    expect(screen.getByText('Đã được người dùng chỉnh sửa')).toBeInTheDocument()
  })
})
