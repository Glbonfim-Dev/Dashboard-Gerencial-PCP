e conteudo no modulo EstaPastaDeTrabalho (ThisWorkbook) para substituir
' a automacao antiga. A publicacao agora e feita pela tarefa central do Windows.
Option Explicit

Private Sub Workbook_AfterSave(ByVal Success As Boolean)
    ' Intencionalmente vazio: qualquer computador pode salvar sem executar Python.
End Sub
