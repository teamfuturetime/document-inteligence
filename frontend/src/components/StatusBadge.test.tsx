import{render,screen}from'@testing-library/react';import{describe,expect,it}from'vitest';import'@testing-library/jest-dom/vitest';import StatusBadge from'./StatusBadge';
describe('StatusBadge',()=>{it('hiển thị nhãn tiếng Việt',()=>{render(<StatusBadge status="confirmed"/>);expect(screen.getByText('Đã xác nhận')).toBeInTheDocument()})})
