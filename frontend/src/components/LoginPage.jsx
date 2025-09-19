import '../styles/Auth.css'
import logo from '../assets/logo.png';

const LoginPage = () => {
  return (
    <>
      <div className='logo-img'>
        <img src={logo} alt="Secure AI Vault Logo" />
      </div>
      <div className='container'>
        <div className='login-header'>
          <h3>Login</h3>
        </div>
        <div className='login-form'>
          <form>
            <div className='form-group'>  
              <label htmlFor='email'>Email</label>
              <input type='email' id='email' name='email' required />
            </div>
            <div className='form-group'>
              <label htmlFor='password'>Password</label>
              <input type='password' id='password' name='password' required />
            </div>
            <button type='submit' className='login-button'>Login</button>
          </form>
        </div>
      </div>  
      
    </>
  )
}

export default LoginPage;