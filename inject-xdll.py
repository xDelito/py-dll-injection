import ctypes
import tkinter as tk
from tkinter import filedialog
import psutil

# Crear una ventana de Tkinter
window = tk.Tk()
window.withdraw()

# Mostrar el cuadro de diálogo de selección de archivos y obtener la ruta del archivo DLL
dll_path = filedialog.askopenfilename(title="Seleccionar archivo DLL")

# Verificar si se seleccionó un archivo
if not dll_path:
    print("No se seleccionó ningún archivo DLL.")
    exit(1)

# Obtener la lista de procesos
processes = list(psutil.process_iter(['pid', 'name']))

# Mostrar una ventana de diálogo para que el usuario seleccione el proceso objetivo
root = tk.Tk()
root.title("Seleccionar proceso objetivo")

# Crear una lista desplegable con los procesos
selected_process_id = tk.StringVar()
selected_process_id.set(str(processes[0].info["pid"]))
processes_dropdown = tk.OptionMenu(root, selected_process_id, *[str(process.info["pid"]) for process in processes])
processes_dropdown.pack()

# Botón para confirmar la selección
confirm_button = tk.Button(root, text="Seleccionar", command=root.destroy)
confirm_button.pack()

# Ejecutar el bucle principal de la aplicación de Tkinter
root.mainloop()

# Obtener el identificador del proceso objetivo seleccionado
target_process_id = int(selected_process_id.get())

# Abre el proceso objetivo con permisos para la inyección de DLL
process_handle = ctypes.windll.kernel32.OpenProcess(
    ctypes.c_int(0x1F0FFF),  # Derechos de acceso requeridos (todos los derechos)
    ctypes.c_int(False),     # Si el proceso debe heredar los manejadores
    ctypes.c_int(target_process_id)  # ID del proceso objetivo
)

if process_handle == 0:
    print("No se pudo abrir el proceso objetivo.")
    exit(1)

# Reserva memoria en el proceso objetivo para la ruta del archivo DLL
dll_path_address = ctypes.windll.kernel32.VirtualAllocEx(
    ctypes.c_int(process_handle),        # Handle del proceso objetivo
    ctypes.c_int(0),                     # Dirección base de la memoria reservada (0 para asignación automática)
    ctypes.c_int(len(dll_path)),          # Tamaño de la memoria reservada
    ctypes.c_int(0x3000),                 # Tipo de asignación de memoria (commit + reserve)
    ctypes.c_int(0x40)                    # Protección de memoria (lectura + escritura)
)

if dll_path_address == 0:
    print("No se pudo reservar memoria en el proceso objetivo.")
    exit(1)

# Escribe la ruta del archivo DLL en la memoria reservada del proceso objetivo
written = ctypes.c_int(0)
ctypes.windll.kernel32.WriteProcessMemory(
    ctypes.c_int(process_handle),    # Handle del proceso objetivo
    ctypes.c_int(dll_path_address),   # Dirección base de la memoria reservada
    ctypes.c_char_p(dll_path.encode()),  # Ruta del archivo DLL
    ctypes.c_int(len(dll_path)),      # Tamaño de los datos a escribir
    ctypes.byref(written)             # Bytes escritos (no se utiliza)
)

# Obtén la dirección de la función LoadLibraryA de kernel32.dll
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
load_library_address = kernel32.GetProcAddress(kernel32._handle, b"LoadLibraryA")

if not load_library_address:
    print("No se pudo obtener la dirección de LoadLibraryA.")
    exit(1)

# Crea un hilo en el proceso objetivo para llamar a LoadLibraryA y cargar la DLL
thread_id = ctypes.windll.kernel32.CreateRemoteThread(
    ctypes.c_int(process_handle),       # Handle del proceso objetivo
    ctypes.c_int(0),                    # Atributos de seguridad (0 para los atributos predeterminados)
    ctypes.c_int(0),                    # Tamaño de pila inicial (0 para el tamaño predeterminado)
    ctypes.c_int(load_library_address),  # Dirección de la función a llamar (LoadLibraryA)
    ctypes.c_int(dll_path_address),      # Argumento para la función (ruta del archivo DLL)
    ctypes.c_int(0),                     # Flags (0 para la ejecución inmediata)
    ctypes.c_int(0)                      # ID del hilo (no se utiliza)
)

if thread_id == 0:
    print("No se pudo crear un hilo en el proceso objetivo.")
    exit(1)

print("DLL inyectada exitosamente en el proceso objetivo.")
