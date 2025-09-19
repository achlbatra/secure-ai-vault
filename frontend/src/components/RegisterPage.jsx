import '../styles/Auth.css';
import logo from '../assets/logo.png';

const RegisterPage = () => {
  return (
    <>
      <div className='logo-img'>
              <img src={logo} alt="Secure AI Vault Logo" />
            </div>
      <div className='container'>
        <div className='login-header'>
          <h3>Sign Up</h3>
          <p>Get started for free!</p>
        </div>
        <div className='login-form'>
          <form>
            <div className='form-group'>  
              <label htmlFor='email'>Email</label>
              <input type='email' id='email' name='email' required />
            </div>
            <div className='form-group'>
              <label htmlFor='role'>Role</label>
              <select id='role' name='role' required>
                <option value='user'>User</option>
                <option value='admin'>Admin</option>
                <option value='compliance'>Compliance</option>
              </select>
            </div>
            <div className='form-group'>
              <label htmlFor='department'>Department</label>
              <input type='text' id='department' name='department' required />
            </div>
            <div className='form-group'>
              <label htmlFor='password'>Password</label>
              <input type='password' id='password' name='password' required />
            </div>
            <button type='submit' className='register-button'>Register</button>
          </form>
        </div>
      </div>  
      
    </>
  )
}

export default RegisterPage;